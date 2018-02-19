from mako.template import Template
from mako.runtime import Context

def generate_things(data):
    things_template = Template(filename="openhab_templates/modbus_things.template")
    things_content = things_template.render(requests_data=data, tcp_data=dict(host="10.8.0.20", port=502, id=1))
    return things_content