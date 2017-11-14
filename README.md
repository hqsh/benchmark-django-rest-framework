# benchmark-django-rest-framework

A introduction for this framework is in https://github.com/hqsh/benchmark_django_rest_framework_demo/blob/master/Introduction/Introduction.md. And the more detail document is in https://github.com/hqsh/benchmark-django-rest-framework/blob/master/benchmark%20django%20rest%20framework%20%E5%90%84%E5%8A%9F%E8%83%BD%E8%AF%A6%E8%A7%A3.docx.

After you installed this framework. Run the command as below in the directory which include the django settings.py file.

python -m benchmark_django_rest_framework.create_benchmark_settings

Then, add the codes as below in the django settings.py file.

BENCHMARK_SETTINGS = 'your_django_project_directory_name.benchmark_settings'

Insert BENCHMARK_SETTINGS into the INSTALLED_APPS.

You can try this demo to know how to use this framework: https://github.com/hqsh/benchmark_django_rest_framework_demo.