from mako.template import Template
from mako.runtime import Context
from ruamel.yaml import YAML
import os
import codecs
import copy

project_map = None
project_name = None

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

tcp_settings = dict(host="10.8.0.20", port=502, id=1, name="TCPconnect")

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

def build_project(project, modbus_data):
    filtered_modbus_data = copy.copy(modbus_data)
    for req_type, data in modbus_data.items():
        if req_type in project:
            req_vars = filtered_modbus_data[req_type]['vars']
            req_vars = list(
                filter(
                    lambda var: var['name'] in list(project[req_type]['fields'].values()), 
                    data['vars']))
            filtered_modbus_data[req_type]['vars'] = req_vars
            filtered_modbus_data[req_type].update(
                dict(start=req_vars[0]['addr'],
                size=req_vars[-1]['addr'] - req_vars[0]['addr'] + req_vars[-1]['size']))
        else:
            del filtered_modbus_data[req_type]

    global output_dir
    output_dir = os.path.join(os.path.dirname(__file__),
                              output_dir,
                              project_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    generate_things(filtered_modbus_data)

    fields = dict()
    items = dict()
    for req_type, data in project.items():
        req_thing_id = filtered_modbus_data[req_type]['id']
        if 'fields' in data:
            fields.update(data['fields'])
        if 'items' in data:
            items.update(data['items'])
            for item_id, _ in data['items'].items():
                item_thing_id = list(filter(lambda item: item['name'] == fields[item_id], filtered_modbus_data[req_type]['vars']))[0]['id']
                items[item_id]['thing_full_name'] = "{}:{}:{}".format(tcp_settings['name'],req_thing_id,item_thing_id)

    generate_items(items)

    generate_maps(items)

    generate_sitemap(items)
    

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