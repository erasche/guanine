import ast, _ast, subprocess, os, argparse
import logging
logging.basicConfig(level=logging.INFO)

def write_files(app_name):
    models = {}

    # parse models.py
    with open('%s/models.py' % app_name) as models_file:
        m = ast.parse(models_file.read())
        for i in m.body:
            if type(i) == _ast.ClassDef:
                models[i.name] = {}
                for x in i.body:
                    if type(x) == _ast.Assign:
                        models[i.name][x.targets[0].id] = x.value.func.attr


    serializer_names = [model+'Serializer' for model in models]

    # serializers.py
    with open('%s/serializers.py' % app_name, 'w') as ser_file:
        def ser_class(model):
            s = "class %sSerializer(serializers.HyperlinkedModelSerializer):\n" % model
            s += "    class Meta:\n"
            s += "        model = %s\n" % model
            s += " "*8 + "fields = (" + ', '.join(["'%s'" % x for x in models[model]]) + ')\n'
            ser_file.write('\n')
            ser_file.write(s)

        ser_file.write('from rest_framework import serializers\n')
        ser_file.write('from %s.models import ' % app_name + ', '.join([model for model in models]) + '\n')
        for model in models:
            ser_class(model)

    # views.py
    with open('%s/views.py' % app_name, 'w') as view_file:
        def viewset_class(model):
            v = "class %sViewSet(viewsets.ModelViewSet):\n" % model
            v += "    queryset = %s.objects.all()\n" % model
            v += "    serializer_class = %sSerializer\n" % model
            view_file.write('\n')
            view_file.write(v)

        view_file.write('from rest_framework import viewsets\n')
        view_file.write('from %s.serializers import ' % app_name + ', '.join([name for name in serializer_names]) + '\n')
        view_file.write('from %s.models import ' % app_name + ', '.join([model for model in models]) + '\n')
        for model in models:
            viewset_class(model)


    # admin.py
    with open('%s/admin.py' % app_name, 'w') as admin_file:
        def admin_class(models):
            for model in models:
                a = "class %sAdmin(admin.ModelAdmin):\n" % model
                a += "    queryset = %s.objects.all()\n" % model
                a += "    " + "list_display = (" + ', '.join(["'%s'" % x for x in models[model] if models[model][x] != 'ManyToManyField'])  + ')\n'
                admin_file.write('\n')
                admin_file.write(a)

        admin_file.write('from django.contrib import admin\n')
        admin_file.write('from .models import ' + ', '.join([model for model in models]) + '\n')
        admin_class(models)
        admin_file.write('\n')
        for model in models:
            admin_file.write("admin.site.register(%(0)s, %(0)sAdmin)\n" % {'0':model})

    # urls.py
    with open('%s/urls.py' % app_name, 'w') as url_file:
        url_file.write('from django.conf.urls import url, include\n')
        url_file.write('from rest_framework import routers\n')
        url_file.write('from %s import views\n' % app_name)
        url_file.write('\n')
        url_file.write('router = routers.DefaultRouter()\n')

        for model in models:
            plural = 's'
            if model.endswith('s'):
                plural = 'es'
            url_file.write("router.register(r'%(0)s', views.%(1)sViewSet)\n" % {'0':model.lower() + plural, '1':model})

        url_file.write('\n')

        u = '\n'.join(["urlpatterns = [",
                       " "*4 + "url(r'^%s/', include(router.urls))," % app_name,
                       "]"])

        url_file.write(u)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Populate serializers, views, urls, and admin based on models.py')
    parser.add_argument('--disable-venv', help='Disable creation of virtual environment', action="store_true")
    parser.add_argument("--app_name", help='App name on which to perform script', default="base")
    args = parser.parse_args()

    write_files(args.app_name)

    my_env = os.environ.copy()
    if not args.disable_venv:
        subprocess.check_call(["virtualenv", "venv"])
        my_env["PATH"] = os.getcwd() + '/venv/bin:'  + my_env["PATH"]

    subprocess.check_call(["pip", "install", "-r", "requirements.txt"], env=my_env)
    subprocess.check_call(["python", "manage.py", "makemigrations", "%s" % args.app_name], env=my_env)
    subprocess.check_call(["python", "manage.py", "migrate"], env=my_env)