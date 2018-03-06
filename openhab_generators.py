from mako.template import Template
from mako.runtime import Context
from ruamel.yaml import YAML
import os
import codecs
import copy
import uuid
import logging

project_map = None
project_name = None

# TODO: move all these variables to config
project_dir = "projects"
project_map_filename = "map.yaml"
project_site_filename = "site.yaml"

output_dir = "output"
output_things_filename = "modbus.things"
output_items_filename = "modbus.items"
output_sitemap_filename = "modbus.sitemap"

template_dir = "openhab_templates"
template_things_filename = "modbus_things.template"
template_items_filename = "modbus_items.template"
template_sitemap_filename = "modbus_sitemap.template"

# TODO: move this to arguments of program and/or config file
tcp_settings = dict(host="10.8.0.20", port=502, id=1, name="TCPconnect")

# read project map.yaml in memory and return it as a dict
# supposing that it will be stored in a projects directory in a subdirectory with the same name, as specified project name
def read_project(name):
    global project_name
    global project_map 
    project_name = name
    yaml = YAML(typ='safe')
    project_map_path = os.path.join(os.path.dirname(__file__), 
                                    project_dir,
                                    project_name, 
                                    project_map_filename)

    with codecs.open(project_map_path, "r", encoding="utf-8") as project_map_file:
        project_map = yaml.load(project_map_file)
    
    return project_map

# helper function to break list l of items with fields 'addr' and 'size' into few lists (chunks)
# each chunk can't be bigger then n 
# note, that distribution of 'addr' inside of l can be very sparse, so it's possible to make parts with only 1 element
def make_chunks(l, n):
    chunks_list = []
    curr_chunk = []
    start_addr = l[0]['addr']
    for var in l:
        if (var['addr'] + var['size'] - start_addr > n):
            chunks_list.append(curr_chunk)
            curr_chunk = []
            start_addr = var['addr']
        curr_chunk.append(var)
    chunks_list.append(curr_chunk)
    return chunks_list

# helper function to calculate size of list c of items with fields 'addr' and 'size'
def chunk_size(c):
    return (c[-1]['addr'] - c[0]['addr'] + c[-1]['size'])

# main function to join read project data and modbus configuration and generate necessary OpenHab's files
def build_project(project, modbus_data):

    # remove not mentioned in 'project' requests from modbus_data
    modbus_data = dict(
        list(
            filter(
                lambda k: k[0] in project, modbus_data.items()
            )
        )
    )

    # remove not mentioned in 'project' fields for each request in modbus_data and calculating starting address and size of request
    extra_modbus_data = dict()
    for req_type, data in modbus_data.items():
        req_vars = modbus_data[req_type]['vars']
        req_vars = list(
            filter(
                lambda var: var['name'] in list(project[req_type]['fields'].values()), 
                data['vars']
            )
        )

        # starting address is the address of the first field in request and size is the distance between the last and the first plus size of the last
        # if size is bigger than 120 then we'll receive an error from OpenHab's modbus binding (code 160)
        # to overcome this without rebuilding modbus binding we'll break such requests into parts
        # this approach will result in separate requests of the same type and separate modbus 'pollers' in 'things'
        chunks = make_chunks(req_vars, 120)

        # there will always be at least one chunk
        req_vars = chunks[0]
        modbus_data[req_type]['vars'] = chunks[0]
        modbus_data[req_type].update(
            dict(
                start=req_vars[0]['addr'],
                size=chunk_size(chunks[0])
            )
        )

        # all additional chunks will be named with index after name (i.e. input0, input1, etc.)
        # each request has its own vars, id, start address and size
        # however it will be transfered into the same poller type as original request by removing index after the name (see things' template)
        # all additional request will be put into extra_modbus_data dict because we can't add items to currently iterated dict modbus_data
        if len(chunks) > 1:
            i = 0
            for chunk in chunks[1:len(chunks)]:
                req_type_incremented = "{}{}".format(req_type, i)
                extra_req = {
                    req_type_incremented: {
                        'vars': chunk,
                        'start': chunk[0]['addr'],
                        'size': chunk_size(chunk),
                        'id': uuid.uuid4()
                    }
                }
                extra_modbus_data.update(extra_req)
                i+=1

    # now we can concatenate two dicts: original and with extra requests
    modbus_data.update(extra_modbus_data)

    # check that output directory exists and mkdir if not
    global output_dir
    output_dir = os.path.join(os.path.dirname(__file__),
                              output_dir,
                              project_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # call generator for .things files based on modbus_data
    generate_things(modbus_data)

    # prepare data for generating items
    # first we need to map native modbus names in vars to more reliable identificators 
    # mapping is made in 'fields' section of each request in project's map.yaml and put in 'fields' dict
    # after thar we join 'items' dict, containing item's specific data for every field, with modbus_data using 'fields' as a reference for names mapping
    fields = dict()
    items = dict()
    for req_type, data in project.items():
        req_thing_id = modbus_data[req_type]['id']
        if 'fields' in data:
            # populate 'fields' dict with items from current request
            fields.update(data['fields'])
        if 'items' in data:
            # populate 'items' dict with items from current request
            items.update(data['items'])

            # need to join 'items' with modbus_data to form full names
            # the only way is to use 'fields' dict as a mapping
            # but we've possibly broken requests into parts in modbus_data so it's a bit more complicated because we need to search our item in every part
            possible_requests = list(
                filter(
                    lambda i: i[0].startswith(req_type), 
                    modbus_data.items()
                )
            )
            for item_id, _ in data['items'].items():                
                req_thing_id = None
                item_thing_id = None
                for req_candidate, req_data in possible_requests:
                    # mapping item name with var name in requests 
                    item_things = list(
                        filter(
                            lambda i: i['name'] == fields[item_id], 
                            req_data['vars']
                        )
                    )
                    # if we've got result (usually 1), then we can obtain thing id both for item and request
                    if len(item_things) != 0:
                        item_thing_id = item_things[0]['id']
                        req_thing_id = modbus_data[req_candidate]['id']

                # its necessary to form full name of thing so we can put it as a part of 'channel' definition in OpenHab's modbus binding (see items' template)
                # full name consists of modbus connection name, thing id and item id joined with :
                # (see https://github.com/ssalonen/openhab2-addons/blob/modbus-openhab2-native-binding/addons/binding/org.openhab.binding.modbus/README.md)
                items[item_id]['thing_full_name'] = "{}:{}:{}".format(tcp_settings['name'],req_thing_id,item_thing_id)


    # call generator for .items files based on 'items' dict
    generate_items(items)

    # call generator for .map files based on 'items' dict
    generate_maps(items)

    # call generator for .sitemap files based on 'items' dict
    generate_sitemap(items)
    
# generate .things file based on modbus_data using things' template
# file will be stored in output directory in a subdirectory with the same name as a project
def generate_things(data):
    template_things_path = os.path.join(os.path.dirname(__file__), 
                                        template_dir, 
                                        template_things_filename)
    things_template = Template(filename=template_things_path)
    things_content = things_template.render(requests_data=data, tcp_data=tcp_settings, local_vars={})
    output_things_path = os.path.join(os.path.dirname(__file__), 
                                      output_dir, 
                                      output_things_filename)
    with codecs.open(output_things_path, "w", encoding="utf-8") as things_file:
        things_file.write(things_content)

# generate .items file based on items data from project config using items' template
# file will be stored in output directory in a subdirectory with the same name as a project
def generate_items(data):
    template_items_path = os.path.join(os.path.dirname(__file__), 
                                       template_dir, 
                                       template_items_filename)
    items_template = Template(filename=template_items_path)
    items_content = items_template.render(items_data=data)
    output_items_path = os.path.join(os.path.dirname(__file__), 
                                     output_dir, 
                                     output_items_filename)

    with codecs.open(output_items_path, "w", encoding="utf-8") as items_file:
        items_file.write(items_content)

# generate .map file(s) based on items data from project config
# each file includes 'mapping' field of each item (if specified) 'as is'
# (see https://docs.openhab.org/addons/transformations/map/readme.html)
# file(s) will be stored in output directory in a subdirectory with the same name as an item
def generate_maps(data):
    output_maps_path = os.path.join(os.path.dirname(__file__), 
                                    output_dir, 
                                    output_items_filename)
    for item, item_data in data.items():
        if ('mapping' in item_data and item_data['mapping'] != None):
            output_maps_path = os.path.join(os.path.dirname(__file__), 
                                            output_dir, 
                                            "{}.map".format(item))
            with codecs.open(output_maps_path, "w", encoding="utf-8") as map_file:
                map_file.write(item_data['mapping'])    

# generate .sitemap file based on items and project's site.yaml using sitemap's template
# file will be stored in output directory in a subdirectory
def generate_sitemap(data):
    yaml = YAML(typ='safe')
    project_site_path = os.path.join(os.path.dirname(__file__), 
                                     project_dir,
                                     project_name, 
                                     project_site_filename)
    with codecs.open(project_site_path, "r", encoding="utf-8") as project_site_file:
        project_site = yaml.load(project_site_file)

    template_sitemap_path = os.path.join(os.path.dirname(__file__), 
                                         template_dir, 
                                         template_sitemap_filename)
    sitemap_template = Template(filename=template_sitemap_path)
    sitemap_content = sitemap_template.render(map=project_site, items=data, name=project_name)

    output_sitemap_path = os.path.join(os.path.dirname(__file__), 
                                       output_dir, 
                                       output_sitemap_filename)
    with codecs.open(output_sitemap_path, "w", encoding="utf-8") as sitemap_file:
        sitemap_file.write(sitemap_content)