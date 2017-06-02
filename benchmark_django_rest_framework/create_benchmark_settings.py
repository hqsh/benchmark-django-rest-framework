# -*- coding:utf-8 -*-
import os

init_data = '''\
# -*- coding:utf-8 -*-

from django.http import JsonResponse
import copy


# The http response json data field names, you can modify them to fit in with your web sit. The SUCCESS_CODE cannot be
# set to any number below 200 (200 is allowed). Otherwise it maybe conflict with the codes defined in this framework.
CODE = 'code'
MSG = 'msg'
DATA = 'data'
SUCCESS_CODE = 0

# The http response json format
# The code 0 represents the successful response. The error codes which smaller than 200 is defined by the framework.
# It's not recommended to define the error codes by the any web site itself.
# http 响应的 json 格式配置
# CODE 为 SUCCESS_CODE 代表成功的响应. 小于 200 的 CODE 用于该框架, 不推荐使用小于 200 的 CODE 用于站点自定义的错误.
# 仅支持对 SUCCESS_CODE 值进行修改成 200 或 200 以上, 否则会有不可预期的结果
DICT_RESPONSE_BY_CODE = {
    '0': {CODE: SUCCESS_CODE, MSG: 'success'},
    '1': {CODE: 1, MSG: 'raise exception'},    # the msg should be replaced by the except reason
    '2': {CODE: 2, MSG: 'request parameters should include "pk" as the primary key for the primary model of the uri'},
    '3': {CODE: 3, MSG: 'this api does not support this http method'},
    '4': {CODE: 4, MSG: 'insert failed: the model has the data with the same primary key as the post data'},
    '5': {CODE: 5, MSG: 'insert failed: one of the relationship keys is already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '6': {CODE: 6, MSG: 'update or delete failed: the data does not exist'},
    '7': {CODE: 7, MSG: 'update or delete failed: the data exist, but is already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '8': {CODE: 8, MSG: 'insert failed: the foreign key (%s = %s) is already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '9': {CODE: 9, MSG: 'insert failed: the foreign key (%s = %s) is not exist'},
    '10': {CODE: 10, MSG: 'update failed: the value of the request data %s cannot be list'},
    '11': {CODE: 11, MSG: 'deleted, but some foreign key has already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '12': {CODE: 12, MSG: 'insert failed: the post request cannot contains "pk" parameter'},
    '13': {CODE: 13, MSG: 'insert failed: the post request should has some legal request data'},
    '14': {CODE: 14, MSG: 'invalid select_related field: '},
    '15': {CODE: 15, MSG: 'request parameter does not exist: '},
    '16': {CODE: 16, MSG: 'request data in body does not exist: '},
    '17': {CODE: 17, MSG: 'the format of date time string in request parameter is not correct, it should like "2017-03-24 20:05:39"'},
    '18': {CODE: 18, MSG: 'the format of date string in request parameter is not correct, it should like "2017-03-24"'},
    '19': {CODE: 19, MSG: 'the format of time string in request parameter is not correct, it should like "20:05:39"'},
    '100': {CODE: 100, MSG: 'login failed'},
    '101': {CODE: 101, MSG: 'anonymous user cannot access this api, should login first'},
}


def GET_RESPONSE_BY_CODE(code=SUCCESS_CODE, msg=None, data=None, msg_append=None):
    if code == SUCCESS_CODE:
        res = copy.deepcopy(DICT_RESPONSE_BY_CODE['0'])
    else:
        res = copy.deepcopy(DICT_RESPONSE_BY_CODE[str(code)])
    if msg:
        if isinstance(msg, str):
            res[MSG] = msg
        elif isinstance(msg, tuple) or isinstance(msg, list):
            res[MSG] = res[MSG] % msg
    if msg_append:
        res[MSG] += msg_append
    if data:
        res[DATA] = data
    else:
        res[DATA] = []
    return res


def GET_HTTP_RESPONSE_BY_CODE(code=SUCCESS_CODE, msg=None, data=None):
    return JsonResponse(GET_RESPONSE_BY_CODE(code, msg, data), json_dumps_params={"indent": 2})


# The params (in urls) should be exist of http requests.
DICT_CHECK_PARAMS = {
    # # The format is as follow, view names, http methods, field names, for example:
    # 'CompanyView': {
    #     'get': ('company_name', ),
    # }
}

# The data (in request bodies) should be exist of http requests.
DICT_CHECK_DATA = {
    # # The format is as follow, view names, http methods, field names, for example:
    # 'CompanyView': {
    #     'post': ('company_id', 'company_name'),
    # }
}

# The not supported methods of the APIs
DICT_VIEW_NOT_SUPPORT_METHODS = {
    # # The format is as follow, view names, http methods, for example:
    # 'CompanyView': ('delete', ),
}

# The keyword of relation field names in models for searching multiple models in http get requests.
# If one request has several related field branches, list them in a list.
SELECT_RELATED = 'select_related'

# The keyword for filter the http get response data fields. If one request has several model field names to filter,
# list them in a list. If the request need a black list for filter (default is white list), add "-" in the front of
# the value of this parameter.
VALUES = 'values'

# The keyword of the begin position of http get response data.
# It usually used with LIMIT keyword, for limit the number of the search result data.
OFFSET = 'offset'

# The keyword of the maximum number of http get response data.
# It usually used with OFFSET keyword, for limit the number of the search result data.
LIMIT = 'limit'

# The keyword of http get requests for the data order.
ORDER_BY = 'order_by'

# The keyword of django Q object for http get request to filter model.
# For example, /employee?Q=[employee_name=EmployeeAX1$employee_id=1|employee_name=EmployeeAX2$employee_id=2,
# department=1$employee_id=1|department=4$employee_id=8] is same as filter model:
# Employee.objects.filter(Q(employee_name=EmployeeAX1, employee_id=1) | Q(employee_name=EmployeeAX2, employee_id=2),
# Q(department=1, employee_id=1) | Q(department=4, employee_id=8))
Q = 'Q'

# The keyword of "or" splitter for several django Q objects.
Q_OR = '|'

# The keyword of "and" splitter in one django Q object.
# You cannot use "&" because it is the splitter for several parameters in http get request.
# And you cannot use "," because it is the splitter of elements in a list in this framework.
Q_AND = '$'

# The keyword of using django multiple databases.
USING = 'using'

# The keyword of django model primary key.
MODEL_PRIMARY_KEY = 'pk'

# When some models use delete flag, the http delete requests don't delete the items of models, but they set the
# delete flag to "True" value. And we should set the delete flag name of the fields as the value of MODEL_DELETE_FLAG.
# If we don't use the delete flag in every models, we just set the value of MODEL_DELETE_FLAG "None".
# 是否使用删除标记位(delete请求不删除数据库表中数据, 而是修改标记位字段). 若使用, 则为删除标记位字段名;
# 若不使用, 则为 None; 可以支持部分 model 使用删除标记位, 其余 model 不使用
MODEL_DELETE_FLAG = None             # 'delete flag'

# The name of the fields in models which defined as "models.DateTimeField(auto_now_add=True)"
# If haven't these fields, to set the value "None".
# model 创建字段, 若没有该字段可以为 None
MODEL_CREATE_TIME = 'create_time'

# The name of the fields in models which defined as "models.DateTimeField(auto_now=True)".
# If haven't these fields, to set the value "None".
# model 修改字段, 若没有该字段可以为 None
MODEL_MODIFY_TIME = 'modify_time'

# The name of the fields in models which define the creator of the items in models, when the views of the models should
# login first. The framework can set the creator field when the items are added by http post method.
# If the models haven't these fields, we can just set the value "None".
# model 创建者字段, 若没有该字段可以为 None
MODEL_CREATOR = 'creator'

# The name of the fields in models which define the last modifier of the items in models, when the views of the models
# should login first. The framework can reset the modifier field when the items are added by http post method or
# modified by http put method.
# If the models haven't these fields, we can just set the value "None".
# model 修改者字段, 若没有该字段可以为 None
MODEL_MODIFIER = 'modifier'

# If MODEL_DELETE_FLAG is not None, we cannot use many to many relation in model defination. We can define them
# manually, and list their names in the tuple. The framework can maintain the relations when http get/post/put/delete.
# 若 model 使用删除标记位, 多对多表不能由 django 本身维护, 该框架可以提供支持, 需要指定多对多表名
# TODO: developing
MANY_TO_MANY_RELATION_MODEL_NAMES = (
    # # For example:
    # 'ProjectTeamToEmployee',
)

# If MODEL_DELETE_FLAG is not None, we cannot use "unique_together" in models. And we should list these unique
# restrictions. The framework can maintain the unique restrictions.
# 若 model 使用删除标记位, 无法使用唯一性约束, 需要定义唯一性约束的字段
DICT_MODEL_UNIQUE_TOGETHER = {
    # # For example, model name, fields in tuples just as they defined in "unique_together":
    # 'Company': (('company_name', ), ),
}

# If we have some fields of the models store the json string, we can list in this tuple, these json can be resolved as
# the correct format in http get response.
# 若有 model 字段实际存储的是 json 串, 在此需要列出这些字段名, 以在 get 请求返回时候, 解析正确
MODEL_JSON_FIELD_NAMES = (
    # # For example:
    # 'employee_info',
)

# Whether the APIs of the site should be used by login
API_NEED_LOGIN = False

# If API_NEED_LOGIN is True, the django anonymous users can request these uris
DO_NOT_NEED_LOGIN_URIS = (
    # # For example:
    # '/company',
)
'''

if __name__ == '__main__':
    red = '\033[1;31m'
    green = '\033[1;32m'
    color_end = '\033[0m'
    has_settings_file = os.path.isfile('./settings.py')
    if not has_settings_file:
        print(red + 'ERROR: You should run this script in the directory which include the django settings.py file.' + color_end)
        exit(1)
    has_benchmark_settings_file = os.path.isfile('./benchmark_settings.py')
    if has_benchmark_settings_file:
        print(red + 'ERROR: The benchmark_settings.py file is already exist.' + color_end)
        exit(1)
    try:
        file = open(os.getcwd() + '/benchmark_settings.py', 'w')
        file.writelines(init_data)
        file.close()
    except Exception as e:
        print(red + 'ERROR: %s' % str(e) + color_end)
        exit(1)
    print(green + 'SUCCESS: benchmark_settings.py is created' + color_end)

