import os
import locale

from flask import Flask

locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")


def create_app(test_config=None) -> Flask:
    application = Flask(__name__, instance_relative_config=True)
    application.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(application.instance_path, "vote.sqlite"),
    )

    if test_config is None:
        application.config.from_pyfile("config.py", silent=True)
    else:
        application.config.from_mapping(test_config)

    try:
        os.makedirs(application.instance_path)
    except OSError:
        pass

    from . import database

    database.init_application(application)

    from . import maintenance

    maintenance.add_maintenance_commands(application)

    from . import authentication

    application.register_blueprint(authentication.blueprint)

    from . import polls

    application.register_blueprint(polls.blueprint)
    application.add_url_rule("/", endpoint="index")

    from . import voters

    application.register_blueprint(voters.blueprint)
    application.cli.add_command(voters.plot_weight_curve)

    return application
