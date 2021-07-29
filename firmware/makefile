.PHONY: all

all: ../dist/main.py ../dist/app/__init__.py ../dist/app/api.py ../dist/app/hal.py ../dist/app/clock.py ../dist/app/self_test.py ../dist/app/settings.py ../dist/app/irrigation.py ../dist/app/templates/index.html ../dist/app/static/css/skeleton.css ../dist/app/static/css/normalize.css ../dist/app/static/images/favicon.png

../dist/main.py: main.py
	../install.sh ../dist/ main.py

../dist/app/__init__.py: app/__init__.py
	../install.sh ../dist/app/ app/__init__.py

../dist/app/api.py: app/api.py
	../install.sh ../dist/app/ app/api.py

../dist/app/hal.py: app/hal.py
	../install.sh ../dist/app/ app/hal.py

../dist/app/clock.py: app/clock.py
	../install.sh ../dist/app/ app/clock.py

../dist/app/self_test.py: app/self_test.py
	../install.sh ../dist/app/ app/self_test.py

../dist/app/settings.py: app/settings.py
	../install.sh ../dist/app/ app/settings.py

../dist/app/irrigation.py: app/irrigation.py
	../install.sh ../dist/app/ app/irrigation.py

../dist/app/templates/index.html: app/templates/index.html
	../copy.sh ../dist/app/templates/ app/templates/index.html

../dist/app/static/css/normalize.css: app/static/css/normalize.css
	../copy.sh ../dist/app/static/css/ app/static/css/normalize.css

../dist/app/static/css/skeleton.css: app/static/css/skeleton.css
	../copy.sh ../dist/app/static/css/ app/static/css/skeleton.css

../dist/app/static/images/favicon.png: app/static/images/favicon.png
	../copy.sh ../dist/app/static/images/ app/static/images/favicon.png
