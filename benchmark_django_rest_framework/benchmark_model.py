# -*- coding:utf-8 -*-

from collections import OrderedDict
from django.db.models import Q
from itertools import chain
import django, json, traceback
import copy, datetime, sys


SETTINGS = getattr(django.conf.settings, 'BENCHMARK_SETTINGS', None)
if SETTINGS is None:
    raise Exception('BENCHMARK_SETTINGS should be defined in django settings.py file, which is the path of '
                    'benchmark_settings file. For example "BENCHMARK_SETTINGS = app_dir.benchmark_settings"')
try:
    SETTINGS = sys.modules[SETTINGS]
except KeyError:
    raise Exception('BENCHMARK_SETTINGS defined in django settings.py file is not correct. Or the __init__.py in app_dir '
                    'haven\'t import the benchmark_settings file. For example '
                    '"import benchmark_django_rest_framework.benchmark_settings"')


class BenchmarkModel(object):
    @staticmethod
    def get_response_by_code(code=SETTINGS.SUCCESS_CODE, msg=None, data=None, msg_append=None):
        return SETTINGS.GET_RESPONSE_BY_CODE(code, msg, data, msg_append)

    @staticmethod
    def get_http_response_by_code(code=SETTINGS.SUCCESS_CODE, msg=None, data=None):
        return SETTINGS.GET_HTTP_RESPONSE_BY_CODE(code, msg, data)

    @classmethod
    def model_has_delete_flag(cls):
        return SETTINGS.MODEL_DELETE_FLAG is not None and hasattr(cls, SETTINGS.MODEL_DELETE_FLAG)

    @classmethod
    def model_get_delete_flag(cls, m):
        if SETTINGS.MODEL_DELETE_FLAG is not None and hasattr(cls, SETTINGS.MODEL_DELETE_FLAG):
            return getattr(m, SETTINGS.MODEL_DELETE_FLAG)
        return None

    @classmethod
    def model_has_modifier(cls):
        return SETTINGS.MODEL_MODIFIER is not None and hasattr(cls, SETTINGS.MODEL_MODIFIER)

    @classmethod
    def model_get_modifier(cls, m):
        if SETTINGS.MODEL_MODIFIER is not None and hasattr(cls, SETTINGS.MODEL_MODIFIER):
            return getattr(m, SETTINGS.MODEL_MODIFIER)
        return None

    @classmethod
    def model_has_modify_time(cls):
        return SETTINGS.MODEL_MODIFY_TIME is not None and hasattr(cls, SETTINGS.MODEL_MODIFY_TIME)

    @classmethod
    def model_get_modify_time(cls, m):
        if SETTINGS.MODEL_MODIFY_TIME is not None and hasattr(cls, SETTINGS.MODEL_MODIFY_TIME):
            return getattr(m, SETTINGS.MODEL_MODIFY_TIME)
        return None

    @classmethod
    def get_unique_together(cls):
        model_name = cls.__name__
        if model_name in SETTINGS.DICT_MODEL_UNIQUE_TOGETHER.keys():
            return SETTINGS.DICT_MODEL_UNIQUE_TOGETHER[model_name]
        return []

    @classmethod
    def get_json(cls, key, value):
        if SETTINGS.MODEL_JSON_FIELD_NAMES is not None and key in SETTINGS.MODEL_JSON_FIELD_NAMES:
            try:
                value = json.loads(value)
            except:
                pass
        return value

    @classmethod
    def get_json_in_dict(cls, dict_item):
        for key, value in dict_item.items():
            dict_item[key] = cls.get_json(key, value)

    @classmethod
    def filter_model(cls, params=None, query_set=None, select_related=None, Qs=None, using='default'):
        model_filter = {}
        if SETTINGS.MODEL_DELETE_FLAG is not None:
            model_filter[SETTINGS.MODEL_DELETE_FLAG] = 0
        if params is not None:
            for key, value in params.items():
                if key not in [SETTINGS.ORDER_BY, SETTINGS.OFFSET, SETTINGS.LIMIT, SETTINGS.PAGE]:
                    model_filter[key] = value
        if query_set is not None and len(model_filter) == 0:
            pass
        elif query_set is None and len(model_filter) == 0:
            query_set = cls.objects.using(using).filter(**model_filter)
        elif query_set is None and len(model_filter) > 0:
            try:
                query_set = cls.objects.using(using).filter(**model_filter)
            except django.core.exceptions.FieldError:
                try:
                    model_filter.pop(SETTINGS.MODEL_DELETE_FLAG)
                    query_set = cls.objects.using(using).filter(**model_filter)
                except Exception as e:
                    return cls.get_response_by_code(1, str(e))
            except Exception as e:
                return cls.get_response_by_code(1, str(e))
        else:
            query_set = query_set.using(using).filter(**model_filter)
        if Qs is not None:
            list_q = []
            for several_q in Qs:
                _several_q = None
                for q in several_q:
                    if _several_q is None:
                        _several_q = Q(**q)
                    else:
                        _several_q |= Q(**q)
                list_q.append(_several_q)
            for q in list_q:
                query_set = query_set.using(using).filter(q)
        if params is not None and SETTINGS.ORDER_BY in params:
            order_by_field_name = params[SETTINGS.ORDER_BY] if params[SETTINGS.ORDER_BY][0] != '-' else params[SETTINGS.ORDER_BY][1:]
            if hasattr(cls, order_by_field_name):
                query_set = query_set.order_by(params[SETTINGS.ORDER_BY])
        if select_related is not None:
            for field in select_related:
                query_set = query_set.select_related(field)
        return query_set

    @classmethod
    def delete_query_set(cls, list_data):
        for data in list_data:
            keys = tuple(data.keys())
            for key in keys:
                if isinstance(data[key], django.db.models.query.QuerySet) or \
                        isinstance(type(data[key]), django.db.models.base.ModelBase):
                    del data[key]
                elif isinstance(data[key], list):
                    cls.delete_query_set(data[key])

    @staticmethod
    def get_location(pre_location_relate):
        if pre_location_relate['location'] is None:
            return [pre_location_relate['field_name']]
        res = copy.deepcopy(pre_location_relate['location'])
        res.append(pre_location_relate['field_name'])
        return res

    @staticmethod
    def model_to_dict(instance, fields=None, exclude=None):
        """
        copy from django.forms.models.model_to_dict, but also return un-editable fields.
        """
        opts = instance._meta
        data = {}
        omit = getattr(SETTINGS, 'OMIT_UN_EDITABLE_FIELDS', False)
        for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if omit and not getattr(f, 'editable', False):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            data[f.name] = f.value_from_object(instance)
        return data

    @classmethod
    def get_select_related(cls, query_set, select_related_fields, list_data):
        for related_field in select_related_fields.keys():
            query_set = query_set.select_related(related_field)
        for i, m in enumerate(query_set):
            dict_m = cls.model_to_dict(m)
            for relate_name, model in select_related_fields.items():
                for relate_model_field in model._meta.get_fields():
                    name = relate_model_field.name
                    if name in (SETTINGS.MODEL_CREATE_TIME, SETTINGS.MODEL_MODIFY_TIME,
                                SETTINGS.MODEL_CREATOR, SETTINGS.MODEL_MODIFIER):
                        continue
                    if relate_model_field.is_relation and name not in select_related_fields.keys():
                        continue
                    related_field = None
                    for _relate_name in relate_name.split('__'):
                        if related_field is None:
                            if not hasattr(m, _relate_name):
                                break
                            related_field = getattr(m, _relate_name)
                        else:
                            if not hasattr(related_field, _relate_name):
                                related_field = None
                                break
                            related_field = getattr(related_field, _relate_name)
                    if related_field is not None and hasattr(related_field, name):
                        value = getattr(related_field, name)
                        if name in dict_m.keys():
                            name = relate_name + '__' + name
                        while name in dict_m.keys():
                            name = name + '__'
                        dict_m[name] = value
            cls.get_json_in_dict(dict_m)
            list_data.append(dict_m)
        return query_set

    @classmethod
    def get_model(cls, params=None, query_set=None, select_related=None, values=None, values_white_list=True, Qs=None, using='default'):
        relates = {}
        relates_keys = []    # relates, 为避免重复的统计进去
        level_relates = []
        list_data = []
        query_set = cls.filter_model(params, query_set, Qs=Qs, using=using)
        if SETTINGS.PAGE not in params.keys():
            try:
                offset = int(params[SETTINGS.OFFSET])
            except:
                offset = 1
            if offset < 1:
                offset = 1
            try:
                limit = int(params[SETTINGS.LIMIT])
            except:
                limit = 0
            if limit < 0:
                limit = 0
            if limit == 0:
                if offset > 1:
                    query_set = query_set[offset-1:]
            else:
                query_set = query_set[offset-1:offset-1+limit]
        if select_related is not None:
            # create data structures of model relations
            num_select_related = []
            for relate in select_related:
                num = relate.count('__')
                while len(num_select_related) <= num:
                    num_select_related.append([])
                num_select_related[num].append(relate)
            for i, num_related in enumerate(num_select_related[1:][::-1]):
                for relate in num_related:
                    index = relate.rfind('__')
                    prefix_field_name = relate[:index]
                    if prefix_field_name not in num_select_related[i-1]:
                        if prefix_field_name not in num_select_related[len(num_select_related)-i-2]:
                            num_select_related[len(num_select_related)-i-2].append(prefix_field_name)
            for num_related in num_select_related:
                for relate in num_related:
                    index = relate.rfind('__')
                    if index != -1:
                        field_name = relate[index+2:]
                        prefix_field_name = relate[:index]
                        model = relates[prefix_field_name]['related_model']
                        pre_relate = relates[prefix_field_name]
                        _pre_relate = pre_relate
                        while _pre_relate is not None and _pre_relate['level_root'] is not None:
                            _pre_relate = _pre_relate['pre_relate']
                        else:
                            pre_root = _pre_relate
                    else:
                        model = cls
                        field_name = relate
                        pre_relate = None
                        pre_root = None
                    field = getattr(model, field_name, None)
                    # many to one / one to one
                    if isinstance(field, django.db.models.fields.related_descriptors.ForwardManyToOneDescriptor):
                        relate_type = 'to_one'    # many to one / one to one
                        related_model = field.field.related_model
                    # reverse one to one
                    elif isinstance(field, django.db.models.fields.related_descriptors.ReverseOneToOneDescriptor):
                        relate_type = 'to_one'    # reverse one to one
                        related_model = field.related.related_model
                    # reverse many to one / many to many / reverse many to many
                    elif isinstance(field, django.db.models.fields.related_descriptors.ReverseManyToOneDescriptor):
                        if isinstance(getattr(field, 'field', None), django.db.models.fields.related.ManyToManyField):
                            if field.reverse:
                                relate_type = 'to_many'    # reverse many to many
                                related_model = field.rel.related_model
                            else:
                                relate_type = 'to_many'    # many to many
                                related_model = field.field.related_model
                        else:
                            relate_type = 'to_many'    # reverse many to one
                            related_model = field.rel.related_model
                    else:
                        return cls.get_response_by_code(14, msg_append=relate)
                    if pre_relate is None:
                        level = 0
                        level_root = None
                    else:
                        level = pre_relate['level']
                        if level == 0:
                            level_root = None
                        else:
                            root = pre_relate
                            while root['level_root'] is not None:
                                root = root['pre_relate']
                            else:
                                level_root = root
                    if relate_type == 'to_many':
                        level += 1
                        level_root = None
                    if level > 0:
                        if level_root is None:
                            if pre_relate is not None:
                                if pre_relate['level_root'] is None:
                                    location = cls.get_location(pre_relate)
                                else:
                                    location = cls.get_location(pre_relate['level_root'])
                            else:
                                location = None
                        else:
                            location = cls.get_location(level_root)
                    else:
                        location = None
                    relates[relate] = {
                        'full_name': relate,
                        'field_name': field_name,
                        'model': model,
                        'related_model': related_model,
                        'relate_type': relate_type,
                        'level': level,
                        'pre_relate': pre_relate,
                        'pre_root': pre_root,
                        'level_root': level_root,
                        'level_nodes': [],
                        'location': location
                    }
                    if level_root is not None and (level, relate) not in relates_keys:
                        level_root['level_nodes'].append(relates[relate])
                        relates_keys.append((level, relate))
                    while level >= len(level_relates):
                        level_relates.append([])
                    if level_root is None and (level, relate) not in relates_keys:
                        level_relates[level].append(relates[relate])
                        relates_keys.append((level, relate))
            # process model relations
            for level, level_relate in enumerate(level_relates):
                if level == 0:
                    if len(level_relate) > 0:
                        select_related_fields = OrderedDict()
                        for root in level_relate:
                            select_related_fields[root['full_name']] = root['related_model']
                        query_set = cls.get_select_related(query_set, select_related_fields, list_data)
                    else:
                        for item in query_set:
                            dict_item = cls.model_to_dict(item)
                            cls.get_json_in_dict(dict_item)
                            list_data.append(dict_item)
                else:
                    for root in level_relate:
                        list_pre_root_objects, list_pre_root_dicts = ([query_set], [list_data]) if root['pre_root'] is \
                            None else (root['pre_root']['list_object_roots'], root['pre_root']['list_dict_roots'])
                        root['list_object_roots'] = []
                        root['list_dict_roots'] = []
                        for pre_root_objects, pre_root_dicts in zip(list_pre_root_objects, list_pre_root_dicts):
                            for pre_root_object, pre_root_dict in zip(pre_root_objects, pre_root_dicts):
                                field_name = root['field_name']
                                field_name_objects = field_name + '__objects__'
                                pre_root_dict[field_name_objects] = getattr(pre_root_object, field_name).all()
                                pre_root_dict[field_name] = []
                                if len(root['level_nodes']) == 0:
                                    for item in pre_root_dict[field_name_objects]:
                                        dict_item = cls.model_to_dict(item)
                                        cls.get_json_in_dict(dict_item)
                                        pre_root_dict[field_name].append(dict_item)
                                else:
                                    select_related_fields = OrderedDict()
                                    for node in root['level_nodes']:
                                        select_related_fields[node['full_name'][len(root['full_name'])+2:]] = node['related_model']
                                    pre_root_dict[field_name_objects] = cls.get_select_related(
                                            pre_root_dict[field_name_objects],
                                            select_related_fields,
                                            pre_root_dict[field_name]
                                    )
                                root['list_object_roots'].append(pre_root_dict[field_name_objects])
                                root['list_dict_roots'].append(pre_root_dict[field_name])
        else:
            for item in query_set:
                dict_item = cls.model_to_dict(item)
                cls.get_json_in_dict(dict_item)
                list_data.append(dict_item)
        cls.delete_query_set(list_data)
        list_data = cls.filter_fields(data=list_data, values=values, values_white_list=values_white_list)
        return cls.get_response_by_code(data=list_data)

    @classmethod
    def filter_fields(cls, data, values, values_white_list=True):
        if isinstance(values, list):
            res = []
            for item in data:
                _item = {}
                for key, value in item.items():
                    if key in values and values_white_list:
                        _item[key] = value
                    elif key not in values and not values_white_list:
                        _item[key] = value
                res.append(_item)
            return res
        return data

    @classmethod
    def get_model_field_names(cls, model=None):
        if model is None:
            model = cls
        field_names = []
        for field in model._meta.get_fields():
            if SETTINGS.MODEL_DELETE_FLAG is None:
                field_names.append(field.name)
            elif field.name not in (
                SETTINGS.MODEL_CREATE_TIME, SETTINGS.MODEL_CREATOR, SETTINGS.MODEL_DELETE_FLAG,
                SETTINGS.MODEL_MODIFIER, SETTINGS.MODEL_MODIFY_TIME
            ):
                field_names.append(field.name)
        return field_names

    # when using delete flag, you cannot define "unique_together" in models.
    # "unique_together" should be define in benchmark_settings.py.
    # "unique_together" function (detect for unique constraint) is processed here.
    @classmethod
    def check_unique_together(cls, data, pk=None, using='default'):
        unique_together = cls.get_unique_together()
        for field_names in unique_together:
            unique_data = {}
            has_unique_together_fields = False
            for field_name in field_names:
                if field_name in data.keys():
                    has_unique_together_fields = True
                    unique_data[field_name] = data[field_name]
                else:
                    unique_together_field = getattr(cls, field_name)
                    if hasattr(unique_together_field, 'field'):
                        unique_together_field = unique_together_field.field
                    unique_data[field_name] = unique_together_field.get_default()
            if cls.model_has_delete_flag():
                unique_data[SETTINGS.MODEL_DELETE_FLAG] = 0
            if has_unique_together_fields:    # check whether has conflicted data by unique constraint in model
                list_keys = []
                query_set = cls.objects.using(using).all()
                for unique_key, unique_value in unique_data.items():
                    if type(unique_value) is list:
                        list_keys.append(unique_key)
                        q = None
                        for _unique_value in unique_value:
                            if q is None:
                                q = Q(**{unique_key: _unique_value})
                            else:
                                q = q | Q(**{unique_key: _unique_value})
                        query_set = query_set.using(using).filter(q)
                    else:
                        query_set = query_set.using(using).filter(**{unique_key: unique_value})
                if pk is not None and len(list_keys) > 0:    # put
                    return cls.get_response_by_code(10, msg=(list_keys,))
                if query_set.exists():
                    if pk is None:    # post
                        return cls.get_response_by_code(5, data=[cls.model_to_dict(_) for _ in query_set])
                    else:             # put
                        for item in query_set:
                            if pk != item.pk:
                                return cls.get_response_by_code(5, data=[cls.model_to_dict(_) for _ in query_set])
        return cls.get_response_by_code()

    @classmethod
    def post_model(cls, data, user=None, using='default'):
        if isinstance(data, dict):
            post_data = [data]
            insert_multiple_data = False
        elif isinstance(data, (list, tuple)):
            post_data = data
            insert_multiple_data = True
        else:
            raise Exception('data should be dict, list or tuple')
        list_many_to_many_relations = []
        # check and process before insert data to database
        for data in post_data:
            many_to_many_relations = {}
            del_keys = []
            foreign_key_add = {}
            foreign_key_del = []
            field_names = cls.get_model_field_names()
            primary_key_name = cls._meta.pk.attname
            exist_item = None
            for key, value in data.items():
                if key in field_names:
                    is_relationship_field = False
                    field = getattr(cls, key)
                    if hasattr(field, 'field'):
                        is_relationship_field = True
                        field = getattr(cls, key).field
                    if not is_relationship_field and field.field_name == primary_key_name \
                            or is_relationship_field and field.name == primary_key_name:
                        if SETTINGS.MODEL_DELETE_FLAG is None:
                            pass    # has checked by serializer
                        else:
                            exist_item = cls.objects.using(using).filter(pk=value).first()
                            if exist_item is not None:
                                if getattr(exist_item, SETTINGS.MODEL_DELETE_FLAG):
                                    setattr(exist_item, SETTINGS.MODEL_DELETE_FLAG, 0)
                                else:
                                    return cls.get_response_by_code(4)
                    if is_relationship_field:
                        if field.many_to_one or field.one_to_one :
                            if SETTINGS.MODEL_DELETE_FLAG:
                                if isinstance(value, list):    # 目前只有多对多关系表会有 list 参数
                                    values = value
                                else:
                                    values = [value]
                                for _value in values:
                                    if field.related_model.objects.using(using).filter(**{field.target_field.name: _value}).exists():
                                        related_item = field.related_model.objects.using(using).get(**{field.target_field.name: _value})
                                        if hasattr(related_item, SETTINGS.MODEL_DELETE_FLAG):
                                            if getattr(related_item, SETTINGS.MODEL_DELETE_FLAG):
                                                return cls.get_response_by_code(8, msg=(key, _value))
                                    else:
                                        return cls.get_response_by_code(9, msg=(key, _value))
                            foreign_key = field.attname
                            foreign_key_add[foreign_key] = data[key]
                            foreign_key_del.append(key)
                        elif field.many_to_many:
                            many_to_many_relations[key] = copy.deepcopy(value)
                            del_keys.append(key)
                else:
                    del_keys.append(key)
            for key in del_keys:
                del data[key]
            data_before_foreign_key_process = copy.deepcopy(data)
            for key in foreign_key_del:
                del data[key]
            for key, value in foreign_key_add.items():
                data[key] = value
            if SETTINGS.MODEL_DELETE_FLAG is not None and exist_item is None:
                res = cls.check_unique_together(data_before_foreign_key_process, using=using)
                if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
                    return res
            list_many_to_many_relations.append(many_to_many_relations)
        # insert data to database
        success_pks = []
        fail_count = 0
        for data, many_to_many_relations in zip(post_data, list_many_to_many_relations):
            foreign_key_does_not_exist_msg = ''
            if exist_item is None:
                list_data = []    # to support batch insert by values of fields in request data in list
                for key, _value in data.items():
                    if isinstance(_value, list):
                        values = _value
                    else:
                        values = [_value]
                    if len(list_data) == 0:
                        for v in values:
                            list_data.append({key: v})
                    else:
                        last_loop_list_data = copy.deepcopy(list_data)
                        first_loop = True
                        for v in values:
                            if first_loop:
                                for d in list_data:
                                    d[key] = v
                                first_loop = False
                            else:
                                for d in last_loop_list_data:
                                    _d = copy.deepcopy(d)
                                    _d[key] = v
                                    list_data.append(_d)
                if len(list_data) == 0:
                    if not insert_multiple_data:
                        return cls.get_response_by_code(13)
                    fail_count += 1
                try:
                    for pd in list_data:
                        exist_item = cls(**pd)
                        if user is not None:
                            if SETTINGS.MODEL_CREATOR is not None and hasattr(exist_item, SETTINGS.MODEL_CREATOR):
                                setattr(exist_item, SETTINGS.MODEL_CREATOR, user)
                            if SETTINGS.MODEL_MODIFIER is not None and hasattr(exist_item, SETTINGS.MODEL_MODIFIER):
                                setattr(exist_item, SETTINGS.MODEL_MODIFIER, user)
                        exist_item.save(using=using)
                        success_pks.append(exist_item.pk)
                except django.db.utils.IntegrityError as e:
                    if hasattr(e, 'args'):
                        if e.args[0] == 1048 or e.args[0].startswith('NOT NULL constraint failed: '):    # field cannot be None (很可能还有其他类型的错误, 待增加)
                            if not insert_multiple_data:
                                return cls.get_response_by_code(1, str(e))
                            fail_count += 1
                    data_ = {}
                    for key, value in data.items():
                        if isinstance(value, list):
                            data_[key + '__in'] = value
                        else:
                            data_[key] = value
                    exist_item = cls.objects.using(using).get(**data_)
                    if SETTINGS.MODEL_DELETE_FLAG is not None and not getattr(exist_item, SETTINGS.MODEL_DELETE_FLAG):    # duplicate entry for unique
                        if not insert_multiple_data:
                            return cls.get_response_by_code(1, str(e))
                        fail_count += 1
                    if SETTINGS.MODEL_DELETE_FLAG is not None and hasattr(exist_item, SETTINGS.MODEL_DELETE_FLAG):
                        setattr(exist_item, SETTINGS.MODEL_DELETE_FLAG, 1)
                    if user is not None and SETTINGS.MODEL_MODIFIER is not None and hasattr(exist_item, SETTINGS.MODEL_MODIFIER):
                        setattr(exist_item, SETTINGS.MODEL_MODIFIER, user)
                    exist_item.save(using=using)
                    success_pks.append(exist_item.pk)
                for key, value in many_to_many_relations.items():
                    if isinstance(value, list):
                        values = value
                    else:
                        values = [value]
                    for v in values:
                        try:
                            getattr(exist_item, key).add(v)
                        except django.db.utils.IntegrityError:
                            foreign_key_does_not_exist_msg += '    ' + key + '=' + v + ' does not exist'
            else:
                try:
                    for key, value in data.items():
                        setattr(exist_item, key, value)
                    if user is not None and SETTINGS.MODEL_MODIFIER is not None and hasattr(exist_item, SETTINGS.MODEL_MODIFIER):
                        setattr(exist_item, SETTINGS.MODEL_MODIFIER, user)
                    exist_item.save(using=using)
                    success_pks.append(exist_item.pk)
                except Exception as e:
                    print(traceback.format_exc())
                    if not insert_multiple_data:
                        return cls.get_response_by_code(1, str(e))
                    fail_count += 1
            if not insert_multiple_data:
                res = cls.get_response_by_code(SETTINGS.SUCCESS_CODE, msg_append=foreign_key_does_not_exist_msg)
                return res
        res = cls.get_response_by_code()
        res[SETTINGS.DATA] = {SETTINGS.MODEL_PRIMARY_KEY: success_pks if len(success_pks) > 1 else success_pks[0]}
        res[SETTINGS.SUCCESS_COUNT] = len(success_pks)
        return res

    @classmethod
    def put_model(cls, data, user=None, using='default'):
        primary_key_name = cls._meta.pk.attname
        if primary_key_name in data.keys():
            if SETTINGS.MODEL_PRIMARY_KEY in data.keys():
                data.pop(primary_key_name)
            else:
                data[SETTINGS.MODEL_PRIMARY_KEY] = data.pop(primary_key_name)
        if SETTINGS.MODEL_PRIMARY_KEY not in data.keys():
            return cls.get_response_by_code(2)
        pk = data.pop(SETTINGS.MODEL_PRIMARY_KEY)
        del_keys = []
        foreign_key_add = {}
        foreign_key_del = []
        field_names = cls.get_model_field_names()
        for key in data.keys():
            if key in field_names:
                field = getattr(cls, key)
                if hasattr(field, 'field'):
                    field = field.field
                else:
                    continue
                if field.many_to_one or field.one_to_one:
                    foreign_key = field.attname
                    foreign_key_add[foreign_key] = data[key]
                    foreign_key_del.append(key)
            else:
                del_keys.append(key)
        for key in del_keys:
            del data[key]
        data_before_foreign_key_process = copy.deepcopy(data)
        for key in foreign_key_del:
            del data[key]
        for key, value in foreign_key_add.items():
            data[key] = value
        try:
            m = cls.objects.using(using).get(pk=pk)
        except:
            return cls.get_response_by_code(6)
        # when using delete flag, you cannot define "unique_together" in models.
        # "unique_together" should be define in config.py.
        # "unique_together" function (detect for unique constraint) is processed here.
        if SETTINGS.MODEL_DELETE_FLAG is not None:
            update_data = cls.model_to_dict(m)
            update_data.update(data)
            res = cls.check_unique_together(data_before_foreign_key_process, pk=m.pk, using=using)
            if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
                return res
        if SETTINGS.MODEL_DELETE_FLAG is not None:
            if getattr(m, SETTINGS.MODEL_DELETE_FLAG):
                return cls.get_response_by_code(7)
        for key, value in data.items():
            setattr(m, key, value)
        if user is not None and SETTINGS.MODEL_MODIFIER is not None and hasattr(m, SETTINGS.MODEL_MODIFIER):
            setattr(m, SETTINGS.MODEL_MODIFIER, user)
        try:
            m.save(using=using)
        except Exception as e:
            print(traceback.format_exc())
            return cls.get_response_by_code(1, str(e))
        return cls.get_response_by_code()

    @classmethod
    def delete_related_models(cls, m=None, pk=None, delete_flag=True, user=None, modifier=None, delete_time=None,
                              using='default'):
        model = cls if m is None else m.__class__
        if m is None:
            try:
                m = cls.objects.using(using).get(pk=pk)
            except:
                return cls.get_response_by_code(6, data={'model': cls.__name__, 'pk': pk})
            if SETTINGS.MODEL_DELETE_FLAG:
                now_delete_flag = True if getattr(m, SETTINGS.MODEL_DELETE_FLAG) != 0 else False
                if now_delete_flag == delete_flag:
                    return cls.get_response_by_code(7, data={'model': cls.__name__, 'pk': pk})
        else:
            now_delete_flag = True if getattr(m, SETTINGS.MODEL_DELETE_FLAG) != 0 else False
            if now_delete_flag == delete_flag:
                return cls.get_response_by_code()
        m_modifier = cls.model_get_modifier(m)
        # m_modify_time = cls.model_get_modify_time(m)
        if delete_flag is False:    # only restore the data with the same modifier and modify time (within 10 seconds)
            if m_modifier is None or (modifier is not None and modifier != m_modifier):
                return cls.get_response_by_code()
        if not cls.model_has_delete_flag():    # 警告: 关联的表如果有 delete flag, 也会被删除
            m.delete(using=using)
            return cls.get_response_by_code()
        else:
            if cls.model_has_modifier() and user is not None:
                if delete_flag:
                    if delete_time is None:
                        delete_time = str(datetime.datetime.now())
                    setattr(m, SETTINGS.MODEL_MODIFIER, user + '|' + delete_time)
                else:
                    setattr(m, SETTINGS.MODEL_MODIFIER, user)
            setattr(m, SETTINGS.MODEL_DELETE_FLAG, 1 if delete_flag else 0)
            m.save(using=using)
            res_data = []
            for field in model._meta.get_fields():
                if field.one_to_many:
                    related_model = field.related_model
                    remote_field_name_in_db = field.remote_field.attname    # name or attname or column
                    query_set = related_model.objects.using(using).filter(**{remote_field_name_in_db: m.pk})
                    for item in query_set:
                        res = cls.delete_related_models(m=item, delete_flag=delete_flag, user=user, modifier=m_modifier,
                                                        delete_time=delete_time, using=using)
                        if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:    # code = 7
                            res_data.append(res[SETTINGS.DATA])
            if len(res_data) > 0:
                return cls.get_response_by_code(11, data=res_data)
        return cls.get_response_by_code()

    @classmethod
    def delete_model(cls, data, user=None, using='default'):
        if 'pk' in data.keys():
            if 'delete_flag' in data.keys():
                delete_flag = data['delete_flag']
            else:
                delete_flag = True
            # check every pk
            if isinstance(data['pk'], list):
                pks = data['pk']
                query_set = cls.objects.using(using).all()
                all_pk = [_.pk for _ in query_set]
                if cls.model_has_delete_flag():
                    all_delete_flag = [False if getattr(_, SETTINGS.MODEL_DELETE_FLAG) == 0 else True for _ in query_set]
                else:
                    all_delete_flag = [False] * len(all_pk)
                for pk in pks:
                    if len(all_pk) > 0:
                        pk_cls = type(all_pk[0])
                        try:
                            pk = pk_cls(pk)
                        except ValueError:
                            return cls.get_response_by_code(6, data={'pk': pk})
                    if pk not in all_pk:
                        return cls.get_response_by_code(6, data={'pk': pk})
                    elif all_delete_flag[all_pk.index(pk)] == delete_flag:
                        return cls.get_response_by_code(7, data={'pk': pk})
            else:
                pk = data['pk']
                pks = [pk]
                try:
                    m = cls.objects.using(using).get(pk=pk)
                except:
                    return cls.get_response_by_code(6, data={'pk': pk})
                m_delete_flag = cls.model_get_delete_flag(m)
                if m_delete_flag is not None:
                    m_delete_flag = False if m_delete_flag == 0 else True
                    if SETTINGS.MODEL_DELETE_FLAG is not None and m_delete_flag == delete_flag:
                        return cls.get_response_by_code(7, data={'pk': pk})
            # delete
            for pk in pks:
                res = cls.delete_related_models(pk=pk, delete_flag=delete_flag, user=user, using=using)
                if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
                    return res
            return cls.get_response_by_code()
        else:
            return cls.get_response_by_code(2)
