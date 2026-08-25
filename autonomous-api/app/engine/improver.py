def improve_code(code: str, feedback:dict):
    if feedback["error"]:
        return code.replace("return", "# fixed\n return")
    return code