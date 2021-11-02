import json

def encode(obj, hint):
  if obj == None:
    return None
  result = hint.etemplate(obj)
  for key in hint.ekeys(obj):
    val = getattr(obj, key)
    if key in hint.especials:
      hint.especials[key](hint, result, val)
    else:
      hint.etypical(result, key, val)
  return result

async def decode_fields(template, dict, hint):
  for key, val in dict.items():
    if key in hint.dspecials:
      await hint.dspecials[key](hint, template, val)
    else:
      hint.dtypical(template, key, val)
  return template
async def decode(dict, hint):
  if dict == None:
    return None
  obj = await hint.dtemplate(dict)
  return await decode_fields(obj, dict, hint)

def simple_etypical(self, dict, key, val): dict[key] = val
def simple_dtypical(self, obj, key, val): setattr(obj, key, val)
def simple_etemplate(self, dict): return {}
def simple_vars(self, obj): return vars(obj)

def make_hint(cls, ekeys):
  if not hasattr(cls, 'etypical'):
    cls.etypical = simple_etypical
  if not hasattr(cls, 'dtypical'):
    cls.dtypical = simple_dtypical
  if not hasattr(cls, 'etemplate'):
    cls.etemplate = simple_etemplate
  cls.dspecials = {}
  cls.especials = {}
  cls.ekeys = ekeys
  for name, func in vars(cls).items():
    if name.startswith('d_'):
      cls.dspecials[name[2:]] = func
    elif name.startswith('e_'):
      cls.especials[name[2:]] = func
  return cls

def slots_keys(cls):
  def get_slots(self, obj): return obj.__slots__ if hasattr(obj, '__slots__') else ()
  return make_hint(cls, get_slots)

def dict_keys(cls):
  def get_dict(self, obj): return obj.__dict__
  return make_hint(cls, get_dict)

def custom_keys(*keys):
  def decorator(cls):
    def custom(self, obj): return keys
    return make_hint(cls, custom)
  return decorator

def no_keys(cls):
  def custom(*_): return ()
  cls.ekeys = custom
  return cls

def sub_hint(name, hint):
  def decorator(cls):
    def e_func(self, dict, val):
      dict[name] = encode(val, hint)
    async def d_func(self, obj, val):
      setattr(obj, name, await decode(val, hint))
    setattr(cls, 'e_' + name, e_func)
    setattr(cls, 'd_' + name, d_func)
    return cls
  return decorator

def e_ignore(*names):
  def decorator(cls):
    def e_func(*_): pass
    for name in names:
      setattr(cls, 'e_' + name, e_func)
    return cls
  return decorator

class Encoder(json.JSONEncoder):
  def default(self, obj):
    if hasattr(obj, 'dictionize__'):
      return encode(obj, obj.dictionize__)
    return json.JSONEncoder.default(self, obj)
