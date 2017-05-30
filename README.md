# benchmark-django-rest-framework

After you installed this framework. Run the command as below in the directory which include the django settings.py file.

python -m benchmark_django_rest_framework.create_benchmark_settings

Then, add the codes as below in the django settings.py file.

BENCHMARK_SETTINGS = 'your_django_project_directory_name.benchmark_settings'

Insert BENCHMARK_SETTINGS into the INSTALLED_APPS.

You can try this demo to know how to use this framework: https://github.com/hqsh/benchmark_django_rest_framework_demo.