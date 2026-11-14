from number_app.storage.files import save_json

def write_result(path,result):
    if path: save_json(path,result)
