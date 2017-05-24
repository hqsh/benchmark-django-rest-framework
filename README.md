# benchmark-django-rest-framework

After you installed this framework. Run the command as below in the directory which include the django settings.py file. It create a file named "benchmark_settings.py" which roles as the django settings.py for this framework.

python -m benchmark_django_rest_framework.create_benchmark_settings

Then add the codes like below in the django settings.py file.

BENCHMARK_SETTINGS = 'your_app_name.benchmark_settings'

If you are new to this framework, there is a demo for it to let you know how to use it: https://github.com/hqsh/benchmark_django_rest_framework_demo.
