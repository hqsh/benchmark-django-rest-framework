# -*- coding:utf-8 -*-

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.serializers import ModelSerializer
import copy
import django
import json
import math
import logging
import rest_framework
import re
import sys


SETTINGS = getattr(django.conf.settings, 'BENCHMARK_SETTINGS', None)
if SETTINGS is None:
    raise Exception('BENCHMARK_SETTINGS should be defined in django settings.py file, which is the path of '
                    'benchmark_settings file. For example "BENCHMARK_SETTINGS = your_site_app_dir.benchmark_settings"')
try:
    SETTINGS = sys.modules[SETTINGS]
except KeyError:
    raise Exception('BENCHMARK_SETTINGS defined in django settings.py file is not correct. The benchmark_settings file '
                    'does not exist.')


class Logger:
    def __init__(self):
        log_str = '\r[%(asctime)s] %(levelname)s: %(message)s'
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.stream_handler.setFormatter(logging.Formatter(log_str))

    def log(self, msg, level='info'):
        self.logger.addHandler(self.stream_handler)
        getattr(self.logger, level)(msg)
        self.logger.removeHandler(self.stream_handler)


class BenchmarkAPIView(APIView):
    class PostSerializer(ModelSerializer):
        class Meta:
            pass

    class PutSerializer(ModelSerializer):
        class Meta:
            pass

    @classmethod
    def init(cls):
        view_name = cls.__name__
        if not hasattr(cls, 'check_params'):
            if view_name in SETTINGS.DICT_CHECK_PARAMS.keys():
                cls.check_params = SETTINGS.DICT_CHECK_PARAMS[view_name]
            else:
                cls.check_params = {'get': (), 'post': (), 'put': (), 'delete': ()}
        if not hasattr(cls, 'check_data'):
            if view_name in SETTINGS.DICT_CHECK_DATA.keys():
                cls.check_data = SETTINGS.DICT_CHECK_DATA[view_name]
            else:
                cls.check_data = {'get': (), 'post': (), 'put': (), 'delete': ()}
        for check in (cls.check_params, cls.check_data):
            for method in ('get', 'post', 'put', 'delete'):
                if method not in check.keys():
                    check[method] = ()
        if not hasattr(cls, 'primary_model'):
            cls.primary_model = None
        if not hasattr(cls, 'view_not_support_methods'):
            if view_name in SETTINGS.DICT_VIEW_NOT_SUPPORT_METHODS.keys():
                cls.view_not_support_methods = SETTINGS.DICT_VIEW_NOT_SUPPORT_METHODS[view_name]
            else:
                cls.view_not_support_methods = ()
        cls.using = getattr(cls, SETTINGS.USING, 'default')
        cls.logger = Logger()
        cls.PostSerializer.Meta.model = cls.primary_model
        cls.PostSerializer.Meta.fields = '__all__'
        cls.PutSerializer.Meta.model = cls.primary_model
        cls.PutSerializer.Meta.fields = '__all__'
        cls.access = getattr(cls, SETTINGS.ACCESS, {'get': 'all', 'post': 'all', 'put': 'all', 'delete': 'all'})
        for method in {'get', 'post', 'put', 'delete'} - set(cls.access.keys()):
            cls.access[method] = 'all'
        cls.is_ready = True

    def __init__(self):
        if not hasattr(self, 'is_ready'):
            self.__class__.init()
        super(BenchmarkAPIView, self).__init__()
        self.request = None
        self.params = {}
        self.uri_params = {}
        self.data = {}
        self.host = None
        self.path = ''
        self.method = ''
        self.offset = None
        self.limit = None
        self.page = None
        self.file = None
        self.user = None
        self.select_related = None
        self.values = None
        self.values_white_list = True
        self.Qs = None

    @staticmethod
    def get_response_by_code(code=SETTINGS.SUCCESS_CODE, msg=None, data=None, msg_append=None):
        return SETTINGS.GET_RESPONSE_BY_CODE(code, msg, data, msg_append)

    @staticmethod
    def get_http_response_by_code(code=SETTINGS.SUCCESS_CODE, msg=None, data=None):
        return SETTINGS.GET_HTTP_RESPONSE_BY_CODE(code, msg, data)

    # 检查请求字段是否存在
    def check_request_param_data(self):
        is_check_params = True
        for param_data, keys in zip((self.params, self.data), (self.check_params[self.method], self.check_data[self.method])):
            for key in keys:    # 必须存在的参数
                if isinstance(key, str):
                    if key not in param_data.keys():
                        return self.get_response_by_code(15 if is_check_params else 16 + SETTINGS.CODE_OFFSET, msg_append=key)
                else:    # 只需存在其中一个的参数组
                    found = False
                    for _key in key:
                        if _key in param_data.keys():
                            found = True
                            break
                    if not found:
                        return self.get_response_by_code(15 if is_check_params else 16 + SETTINGS.CODE_OFFSET, msg_append=key)
            is_check_params = False
        return self.get_response_by_code()

    # 提取请求 body 中的 data 或 json
    def get_request_data_json(self, request):
        if not hasattr(request, 'body'):
            return {}
        post_data = copy.deepcopy(self.data)
        try:
            res = json.loads(str(request.body, encoding='utf-8'))
        except json.decoder.JSONDecodeError:
            res = {key: value for key, value in post_data.items()}
        return res

    @staticmethod
    def get_uri_params(uri_params):
        if len(uri_params) == 0:
            return {}
        if len(uri_params) == 1:
            return {SETTINGS.MODEL_PRIMARY_KEY: uri_params[0]}
        raise Exception('too many uri params')

    # when using delete flag, you cannot define "unique_together" in models.
    # "unique_together" should be define in config.py.
    # "unique_together" function (detect for unique constraint) is processed here.
    @classmethod
    def check_unique_together(cls, data, pk=None):
        for field_names in cls.unique_together:
            unique_post_data = {}
            for field_name in field_names:
                has_unique_together_fields = False
                if field_name in data.keys():
                    has_unique_together_fields = True
                    unique_post_data[field_name] = data[field_name]
                else:
                    unique_together_field = getattr(cls.primary_model, field_name)
                    if hasattr(unique_together_field, 'field'):
                        unique_together_field = unique_together_field.field
                    unique_post_data[field_name] = unique_together_field.get_default()
                if hasattr(cls.primary_model, SETTINGS.MODEL_DELETE_FLAG):
                    unique_post_data[SETTINGS.MODEL_DELETE_FLAG] = 0
                if has_unique_together_fields:
                    query_set = cls.primary_model.objects.filter(**unique_post_data)
                    if query_set.exists():
                        if pk is None:
                            return cls.get_response_by_code(5 + SETTINGS.CODE_OFFSET)
                        else:
                            for item in query_set:
                                if pk != item.pk:
                                    return cls.get_response_by_code(5 + SETTINGS.CODE_OFFSET)
        return cls.get_response_by_code()

    @classmethod
    def check_primary_model(cls, function_name):
        if cls.primary_model is None:
            raise Exception('primary_model is None, you cannot use this default framework function: %s' % function_name)

    # get 请求对应的 model 操作，对请求 uri 对应的所有 model（支持所有字段）进行过滤操作后对 query set 按 get_data_method 函数进行取值
    def get_model(self):
        self.check_primary_model('get_model')
        params = self.params
        params.update(self.uri_params)
        return self.primary_model.get_model(
            params=params, select_related=self.select_related, values=self.values,
            values_white_list=self.values_white_list, Qs=self.Qs, using=self.using
        )

    def serializer_check(self, data):
        if isinstance(data, dict):
            list_data = [data]
        elif isinstance(data, (list, tuple)):
            list_data = data
        else:
            raise Exception('data should be dict, list or tuple')
        for data in list_data:
            if self.method == 'post':
                serializer = self.PostSerializer(data=data)
            elif self.method == 'put':
                serializer = self.PutSerializer(data=data)
                for field_value in serializer.fields.values():
                    field_value.required = False
            try:
                serializer.is_valid(raise_exception=True)
            except rest_framework.exceptions.ValidationError as e:
                if SETTINGS.MODEL_DELETE_FLAG is None:
                    exception_detail = e.detail
                else:
                    exception_detail = {}
                    for key, errors in e.detail.items():
                        for error in errors:
                            if re.match(r'[\w\d_]+ with this [\w\d_ ]+ id already exists.', error):
                                errors.remove(error)
                        if len(errors) != 0:
                            exception_detail[key] = errors
                if len(exception_detail) > 0:
                    return self.get_response_by_code(20 + SETTINGS.CODE_OFFSET, data=exception_detail)
            except Exception as e:
                return self.get_response_by_code(1 + SETTINGS.CODE_OFFSET, msg=str(e))
        return None

    # post 请求对应的 model 操作
    def post_model(self, data=None):
        self.check_primary_model('post_model')
        post_data = copy.deepcopy(self.data)
        if data:
            if isinstance(post_data, dict):
                post_data.update(data)
            elif isinstance(post_data, (list, tuple)):
                for pd in post_data:
                    pd.update(data)
            else:
                raise Exception('data should be dict, list or tuple')
        res = self.serializer_check(post_data)
        if res is not None:
            return res
        if isinstance(post_data, dict):
            if SETTINGS.MODEL_PRIMARY_KEY in post_data.keys():
                return self.get_response_by_code(12 + SETTINGS.CODE_OFFSET)
        elif isinstance(post_data, (list, tuple)):
            for pd in post_data:
                if SETTINGS.MODEL_PRIMARY_KEY in pd.keys():
                    return self.get_response_by_code(12 + SETTINGS.CODE_OFFSET)
        else:
            raise Exception('data should be dict, list or tuple')
        return self.primary_model.post_model(post_data, user=self.user.get_username(), using=self.using)

    def get_uri_params_data(self, data=None):
        post_data = copy.deepcopy(self.data)
        if data:
            post_data.update(data)
        post_data.update(self.uri_params)
        return post_data

    # put 请求对应的 model 操作，仅可对 primary_model 进行操作
    def put_model(self, data=None):
        self.check_primary_model('put_model')
        post_data = self.get_uri_params_data(data)
        res = self.serializer_check(post_data)
        if res is not None:
            return res
        return self.primary_model.put_model(post_data, user=self.user.get_username(), using=self.using)

    # delete 请求对应的 model 操作
    def delete_model(self):
        self.check_primary_model('delete_model')
        data = copy.deepcopy(self.data)
        data.update(self.uri_params)
        return self.primary_model.delete_model(data, user=self.user.get_username(), using=self.using)

    def check_access(self, pk=None):
        if self.access[self.method] == 'all':    # every one can access
            return self.get_response_by_code()
        if self.access[self.method] is None:    # no one can access
            return self.get_response_by_code(3 + SETTINGS.CODE_OFFSET)
        if not self.user.is_authenticated():
            return self.get_response_by_code(21 + SETTINGS.CODE_OFFSET)
        if self.access[self.method] == 'user':    # login user can access
            return self.get_response_by_code()
        if self.access[self.method] == 'staff':    # staff or admin can access
            return self.get_response_by_code() if self.user.is_staff or self.user.is_superuser else self.get_response_by_code(22 + SETTINGS.CODE_OFFSET)
        if self.access[self.method] == 'superuser':    # superuser can access
            return self.get_response_by_code() if self.user.is_superuser else self.get_response_by_code(22 + SETTINGS.CODE_OFFSET)
        if self.access[self.method] == 'creator':    # creator or admin can access put or delete method
            if SETTINGS.MODEL_CREATOR not in self.primary_model._meta.get_fields():
                raise Exception('primary model %s has no field %s' % (self.primary_model.__name__, SETTINGS.MODEL_CREATOR))
            if pk is None:
                return self.get_response_by_code(2 + SETTINGS.CODE_OFFSET)
            if not isinstance(pk, (list, tuple)):
                pk = [pk]
            if SETTINGS.MODEL_DELETE_FLAG is None:
                query_set = self.primary_model.objects.filter(pk__in=pk)
                if query_set.count == 0:
                    return self.get_response_by_code(6 + SETTINGS.CODE_OFFSET)
            else:
                query_set = self.primary_model.objects.filter(**{'pk__in': pk, SETTINGS.MODEL_DELETE_FLAG: 0})
                if query_set.count == 0:
                    return self.get_response_by_code(7 + SETTINGS.CODE_OFFSET)
            not_creator_pks = []
            for item in query_set:
                creator = getattr(item, SETTINGS.MODEL_CREATOR, None)
                if creator != self.user.username:
                    not_creator_pks.append(item.pk)
            if len(not_creator_pks) > 0:
                return self.get_response_by_code(23 + SETTINGS.CODE_OFFSET)
        raise Exception('unknown access type %s, choices are None, "all", "user", "staff", "superuser", "creator"' %
                        self.access[self.method])

    @staticmethod
    def java_to_python(string):
        new_string = ''
        for alphabet in string:
            if alphabet.isupper():
                new_string = new_string + '_' + alphabet.lower()
            else:
                new_string = new_string + alphabet
        return new_string

    def java_to_python_keys(self):
        if SETTINGS.TRANSFER_KEYS:
            for is_params, param_data in zip((True, False), (self.params, self.data)):
                keys = list(param_data.keys())
                for key in keys:
                    if key in SETTINGS.KEYWORDS_WITH_VALUE_NEED_TRANSFER:
                        value = param_data[key]
                        if isinstance(value, list):
                            for i, v in enumerate(value):
                                value[i] = self.java_to_python(v)
                        else:
                            param_data[key] = self.java_to_python(value)
                    else:
                        param_data[self.java_to_python(key)] = param_data.pop(key)

    @staticmethod
    def python_to_java(string):
        new_string = ''
        to_upper = False
        for i, alphabet in enumerate(string):
            if to_upper:
                if alphabet.islower():
                    new_string = new_string + alphabet.upper()
                else:
                    new_string = new_string + alphabet
                to_upper = False
            elif alphabet == '_':
                if i + 1 < len(string):
                    if string[i + 1] == '_':
                        new_string = new_string + alphabet
                        continue
                if i - 1 > 0:
                    if string[i - 1] == '_':
                        new_string = new_string + alphabet
                        continue
                to_upper = True
            else:
                new_string = new_string + alphabet
        return new_string

    def python_to_java_keys(self, res):
        if SETTINGS.TRANSFER_KEYS:
            if isinstance(res, dict):
                keys = list(res.keys())
                for key in keys:
                    if isinstance(res[key], (dict, list)):
                        self.python_to_java_keys(res[key])
                    new_key = self.python_to_java(key)
                    if key != new_key:
                        res[new_key] = res.pop(key)
            elif isinstance(res, list):
                for item in res:
                    self.python_to_java_keys(item)

    def json_to_string_keys(self):
        if isinstance(self.data, dict):
            post_data = [self.data]
        elif isinstance(self.data, (list, tuple)):
            post_data = self.data
        else:
            raise Exception('data should be dict, list or tuple')
        for data in post_data:
            keys = list(data.keys())
            for key in keys:
                if key in SETTINGS.MODEL_JSON_FIELD_NAMES:
                    data[key] = json.dumps(data[key])

    # 处理各种请求的入口，解析各字段并进行处理
    def begin(self, request, uri_params={}):
        self.request = request
        self.user = request.user
        self.host = request.get_host()
        self.path = request.path
        self.method = request.method.lower()
        self.file = request.FILES.get(SETTINGS.FILE, None)
        if self.method in self.view_not_support_methods:
            return self.get_response_by_code(3 + SETTINGS.CODE_OFFSET)
        self.params = {}
        for key, value in request.GET.items():
            len_value = len(value)
            if len_value >= 2 and value[0] == '[' and value[len_value - 1] == ']':
                value = value[1:-1].split(',')
            elif key == SETTINGS.VALUES and len_value > 3 and value[:2] == '-[' and value[len_value - 1] == ']':
                self.values_white_list = False
                value = value[2:-1].split(',')
            elif key == SETTINGS.VALUES and len_value > 2 and value[0] == '-':
                self.values_white_list = False
                value = value[1:].split(',')
            if key == SETTINGS.SELECT_RELATED:
                if isinstance(value, str):
                    value = [value]
                self.select_related = value
            elif key == SETTINGS.VALUES:
                if isinstance(value, str):
                    value = [value]
                self.values = value
            elif key == SETTINGS.Q:
                if not isinstance(value, list):
                    value = [value]
                self.Qs = []
                for several_q in value:
                    list_q = several_q.split(SETTINGS.Q_OR)
                    _several_q = []
                    for q in list_q:
                        _q = {}
                        list_param_value = q.split(SETTINGS.Q_AND)
                        for param_value in list_param_value:
                            param_name, param_value = param_value.split('=')
                            _q[param_name] = param_value
                        _several_q.append(_q)
                    self.Qs.append(_several_q)
            else:
                self.params[key] = value
        self.uri_params = uri_params
        if self.method == 'get':
            self.offset = self.params.pop(SETTINGS.OFFSET, None)
            self.limit = self.params.pop(SETTINGS.LIMIT, None)
            self.page = self.params.pop(SETTINGS.PAGE, None)
        elif self.method in ('post', 'put', 'delete'):
            request_data = copy.deepcopy(request.data)
            if isinstance(request_data, dict):
                self.data = {}
                try:
                    for key, value in request_data.lists():
                        if len(value) == 1:
                            self.data[key] = value[0]
                        else:
                            self.data[key] = value
                except:
                    for key, value in request_data.items():
                        self.data[key] = value
            elif isinstance(request_data, (list, tuple)):
                self.data = []
                for one_request_data in request_data:
                    one_data = {}
                    try:
                        for key, value in one_request_data.lists():
                            if len(value) == 1:
                                one_data[key] = value[0]
                            else:
                                one_data[key] = value
                    except:
                        for key, value in one_request_data.items():
                            one_data[key] = value
                    self.data.append(one_data)
            else:
                raise Exception('data should be dict, list or tuple')
        res = self.check_request_param_data()
        if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
            return res
        pk = None
        if self.method in ('put', 'delete'):
            if 'pk' in self.uri_params:
                pk = self.uri_params['pk']
            elif 'pk' in self.data:
                pk = self.data['pk']
        if SETTINGS.TRANSFER_KEYS:
            self.java_to_python_keys()
        self.json_to_string_keys()
        return self.check_access(pk=pk)

    # 处理各种类型的返回
    def process_response(self, res):
        if isinstance(res, dict):    # dict 转 json 返回
            if SETTINGS.DATA_STYLE == 'dict':
                if isinstance(res[SETTINGS.DATA], (list, dict)) and len(res[SETTINGS.DATA]) == 0:
                    res[SETTINGS.DATA] = None
                elif isinstance(res[SETTINGS.DATA].get(SETTINGS.RESULT, None), (list, dict)) and len(res[SETTINGS.DATA][SETTINGS.RESULT]) == 0:
                    res[SETTINGS.DATA][SETTINGS.RESULT] = None
            if SETTINGS.TRANSFER_KEYS:
                self.python_to_java_keys(res)
            return JsonResponse(res, json_dumps_params={"indent": 2})
        if isinstance(res, (StreamingHttpResponse, django.http.response.HttpResponse)):    # 流文件, 或已处理好的 http 响应
            return res
        raise Exception('unknown response type: %s' % type(res))

    # 处理 style 2 的 get 请求分页
    def paginate(self, res):
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE and SETTINGS.DATA_STYLE == 'dict':
            # get one
            if 'pk' in self.uri_params.keys():
                if len(res[SETTINGS.DATA]) == 0:
                    res[SETTINGS.DATA] = None
                else:
                    res[SETTINGS.DATA] = res[SETTINGS.DATA][0]
            # get many in pages
            elif self.page is not None:
                try:
                    page = int(self.page)
                except:
                    page = 1
                count = len(res[SETTINGS.DATA])
                try:
                    limit = int(self.limit)
                except:
                    limit = 0
                if limit < 0:
                    limit = 0
                if limit == 0:
                    page_count = 0 if count == 0 else 1
                else:
                    page_count = math.ceil(count / limit)
                if 1 <= page <= page_count:
                    if limit == 0:
                        result = res[SETTINGS.DATA]
                    else:
                        result = res[SETTINGS.DATA][(page - 1) * limit: page * limit]
                else:
                    result = None
                if page < 1:
                    page = 0
                elif page > page_count:
                    page = page_count + 1
                basic_url = 'http://' + self.host + self.path
                previous_param_url = None
                next_param_url = None
                params = copy.deepcopy(self.params)
                params[SETTINGS.LIMIT] = limit
                params[SETTINGS.PAGE] = page
                if page <= 1:
                    previous_url = None
                else:
                    for key, value in params.items():
                        if key == 'page':
                            value = str(page - 1)
                        if previous_param_url is None:
                            previous_param_url = '?' + key + '=' + str(value)
                        else:
                            previous_param_url += '&' + key + '=' + str(value)
                    previous_url = basic_url + previous_param_url
                if page >= page_count:
                    next_url = None
                else:
                    for key, value in params.items():
                        if key == 'page':
                            value = str(page + 1)
                        if next_param_url is None:
                            next_param_url = '?' + key + '=' + str(value)
                        else:
                            next_param_url += '&' + key + '=' + str(value)
                    next_url = basic_url + next_param_url
                res[SETTINGS.DATA] = {SETTINGS.RESULT: result, SETTINGS.COUNT: count,
                                      SETTINGS.NEXT: next_url, SETTINGS.PREVIOUS: previous_url}
            # get many not in pages
            else:
                res[SETTINGS.DATA] = {SETTINGS.RESULT: res[SETTINGS.DATA], SETTINGS.COUNT: len(res[SETTINGS.DATA])}

    # 处理 get 请求
    def get(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.get_model()
        if isinstance(res, dict) and SETTINGS.CODE in res.keys() and res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            self.paginate(res)
        return self.process_response(res)

    # 处理 post 请求
    def post(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.post_model()
        return self.process_response(res)

    # 处理 put 请求
    def put(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.put_model()
        return self.process_response(res)

    # 处理 delete 请求
    def delete(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.delete_model()
        return self.process_response(res)
