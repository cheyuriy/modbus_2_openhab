from mako.template import Template
from mako.runtime import Context
from ruamel.yaml import YAML
import os
import codecs
import copy

project_map = None
project_dir = "projects"
output_dir = "output"
project_map_filename = "map.yaml"
output_things_filename = "modbus.things"

def read_project(project_name):
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
        if project[req_type] != None:
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
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_things_path = os.path.join(os.path.dirname(__file__), 
                                      output_dir, 
                                      output_things_filename)
    with codecs.open(output_things_path, "w", encoding="utf-8") as things_file:
        things_file.write(generate_things(filtered_modbus_data))
    

def generate_things(data):
    things_template = Template(filename="openhab_templates/modbus_things.template")
    things_content = things_template.render(requests_data=data, tcp_data=dict(host="10.8.0.20", port=502, id=1))
    return things_content