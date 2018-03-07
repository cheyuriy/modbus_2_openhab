import csv
import itertools
import uuid

requests_conversion = {
    'INPUT_REGISTERS': "input",
    'COILS': "coil",
    'HOLDING_REGISTERS': "holding",
    'DISCRETE_INPUTS': "discrete"
}

types_conversion = {
    'float': "float32_swap",
    'bool': "bit",
    'int16': "uint16"
}

type_sizes = dict(float=2, int16=1, bool=1)

def parse(file, enc):
    result = dict()
    with open(file, "r", encoding=enc, newline='') as opened_file:
        opened_file_content = list(csv.reader(opened_file, delimiter=';'))
        opened_file_content = opened_file_content[1:]
        request = itertools.groupby(opened_file_content, lambda i: i[1])
        for (req, l) in request:
            req = requests_conversion[req]
            vars_list = make_vars(l)
            start = vars_list[0]['addr']
            size = vars_list[-1]['addr'] - start + vars_list[-1]['size']
            result[req] = {
                'vars': vars_list,
                'start': start,
                'size': size,
                'id': uuid.uuid4()
            }

    return result

def make_vars(l):
    vars = list()
    l = sorted(l, key=lambda i: int(i[2]))
    for item in l:
        var = {
            'name': item[0],
            'type': types_conversion[item[3]],
            'size': type_sizes[item[3]],
            'addr': int(item[2]),
            'id': uuid.uuid4()
        }
        vars.append(var)
    return vars
