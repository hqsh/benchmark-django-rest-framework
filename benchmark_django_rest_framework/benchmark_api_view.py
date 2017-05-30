# -*- coding:utf-8 -*-

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.views import APIView
import copy, django, json, logging, sys


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
        cls.logger = Logger()
        cls.is_ready = True

    def __init__(self):
        if not hasattr(self, 'is_ready'):
            self.__class__.init()
        super(BenchmarkAPIView, self).__init__()
        self.params = {}
        self.uri_params = {}
        self.data = {}
        self.path = ''
        self.method = ''
        self.user = None
        self.path = None
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
        for param_data, keys in zip((self.params, self.data), (self.check_params[self.method], self.check_data[self.method])):
            if keys == self.check_params[self.method]:
                err_code = 15
            else:
                err_code = 16
            for key in keys:    # 必须存在的参数
                if isinstance(key, str):
                    if key not in param_data.keys():
                        return self.get_response_by_code(err_code, msg_append=key)
                else:    # 只需存在其中一个的参数组
                    found = False
                    for _key in key:
                        if _key in param_data.keys():
                            found = True
                            break
                    if not found:
                        return self.get_response_by_code(err_code, msg_append=key)
        return self.get_response_by_code(0)

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

    # @classmethod
    # def get_model_field_names(cls, model=None):
    #     if model is None:
    #         model = cls.primary_model
    #     field_names = []
    #     for field in model._meta.get_fields():
    #         if SETTINGS.MODEL_DELETE_FLAG is None:
    #             field_names.append(field.name)
    #         elif field.name not in (
    #             SETTINGS.MODEL_CREATE_TIME, SETTINGS.MODEL_CREATOR, SETTINGS.MODEL_DELETE_FLAG,
    #             SETTINGS.MODEL_MODIFIER, SETTINGS.MODEL_MODIFY_TIME
    #         ):
    #                 field_names.append(field.name)
    #     return field_names

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
                            return cls.get_response_by_code(5)
                        else:
                            for item in query_set:
                                if pk != item.pk:
                                    return cls.get_response_by_code(5)
        return cls.get_response_by_code(0)

    @classmethod
    def check_primary_model(cls, function_name):
        if cls.primary_model is None:
            raise Exception('primary_model is None, you cannot use this default framework function: %s' % function_name)

    # get 请求对应的 model 操作，对请求 uri 对应的所有 model（支持所有字段）进行过滤操作后对 query set 按 get_data_method 函数进行取值
    def get_model(self):
        self.check_primary_model('get_model')
        params = self.params
        params.update(self.uri_params)
        res = self.primary_model.get_model(params=params, select_related=self.select_related, values=self.values,
                                           values_white_list=self.values_white_list, Qs=self.Qs
                                           )
        # if type(data) == dict and SETTINGS.CODE in data.keys() and SETTINGS.MSG in data.keys() and \
        #         len(data) == 2 and data[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
        #     return data
        # res = self.get_response_by_code(SETTINGS.SUCCESS_CODE)
        # res[SETTINGS.DATA] = data
        return res

    # post 请求对应的 model 操作
    def post_model(self, data=None):
        self.check_primary_model('post_model')
        post_data = copy.deepcopy(self.data)
        if data:
            post_data.update(data)
        if SETTINGS.MODEL_PRIMARY_KEY in post_data.keys():
            return self.get_response_by_code(12)
        return self.primary_model.post_model(post_data, user=self.user.get_username())

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
        return self.primary_model.put_model(post_data, user=self.user.get_username())

    # delete 请求对应的 model 操作
    def delete_model(self):
        self.check_primary_model('delete_model')
        data = copy.deepcopy(self.data)
        data.update(self.uri_params)
        return self.primary_model.delete_model(data, user=self.user.get_username())

    # 处理各种请求的入口，解析各字段并进行处理
    def begin(self, request, uri_params={}):
        self.user = request.user
        self.path = request.path
        need_login = getattr(self.__class__, 'need_login', None)
        if need_login is None:
            if SETTINGS.API_NEED_LOGIN and isinstance(self.user, django.contrib.auth.models.AnonymousUser) and \
                            self.path not in SETTINGS.DO_NOT_NEED_LOGIN_URIS:
                return self.get_response_by_code(101)
        elif need_login and isinstance(self.user, django.contrib.auth.models.AnonymousUser):
            return self.get_response_by_code(101)
        self.method = request.method.lower()
        if self.method in self.view_not_support_methods:
            return self.get_response_by_code(3)
        self.params = {}
        for key, value in request.GET.items():
            len_value = len(value)
            if len_value >= 2 and value[0] == '[' and value[len_value-1] == ']':
                value = value[1:-1].split(',')
            elif key == SETTINGS.VALUES and len_value > 3 and value[:2] == '-[' and value[len_value-1] == ']':
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
        if self.method in ('post', 'put', 'delete'):
            request_data = copy.deepcopy(request.data)
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
        res = self.check_request_param_data()
        if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
            return res
        return self.get_response_by_code(SETTINGS.SUCCESS_CODE)

    # 处理各种类型的返回
    @staticmethod
    def process_response(res):
        if isinstance(res, dict):    # dict 转 json 返回
            return JsonResponse(res, json_dumps_params={"indent": 2})
        if isinstance(res, StreamingHttpResponse):    # 流文件返回
            return res
        raise Exception('unknown response type: %s' % type(res))

    # 处理 get 请求
    def get(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.get_model()
        return self.process_response(res)

    # 处理 post 请求
    def post(self, request):
        res = self.begin(request)
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
