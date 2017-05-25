# benchmark-django-rest-framework

After you installed this framework. Run the command as below in the directory which include the django settings.py file.

python -m benchmark_django_rest_framework.create_benchmark_settings

Then, add the codes as below in the django settings.py file.

BENCHMARK_SETTINGS = 'your_django_project_directory_name.benchmark_settings'

Last, add the codes as below in "__init__.py" file in your django project directory.

import your_django_project_directory_name.benchmark_settings
