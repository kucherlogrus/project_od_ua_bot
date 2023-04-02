import json

class DictToObj:

    class Obj:
        def __str__(self):
            data = []
            for key, value in self.__dict__.items():
                if isinstance(value, self.__class__):
                    atr_data = value.__str__()
                    atr_data = atr_data.replace("\n", "\n\t")
                    atr_data = "\t" + atr_data
                    data.append(f"{key}: \n{atr_data}")
                    continue
                data.append(f"{key}: {value}")
            return "\n".join(data)

        def __repr__(self):
            return self.__str__()

    def __init__(self, data: dict):
        self._data = data

    def dict_data_to_object(self):
        obj = DictToObj.Obj()
        for key, value in self._data.items():
            if isinstance(value, dict):
                value = DictToObj(value).dict_data_to_object()
            if isinstance(value, list):
                value = [DictToObj(v).dict_data_to_object() if isinstance(v, dict) else v for v in value]
            setattr(obj, key, value)
        return obj

    @staticmethod
    def gen_obj(data: dict or str):
        if isinstance(data, str):
            data = json.loads(data)
        return DictToObj(data).dict_data_to_object()