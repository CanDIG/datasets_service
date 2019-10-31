#!/usr/bin/env python3

"""
Driver program for service
"""

import sys
import argparse
import logging

import connexion
import pkg_resources

from tornado.options import define
import candig_dataset_service.orm


def main(args=None):
    """
    Main Routine
    Parse all the args and set up peer and service dictionaries
    """
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser('Run dataset service')
    parser.add_argument('--port', default=8870)
    parser.add_argument('--host', default='ga4ghdev01.bcgsc.ca')
    parser.add_argument('--database', default='./data/datasets.db')
    parser.add_argument('--logfile', default="./log/datasets.log")
    parser.add_argument('--loglevel', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'])
    # parser.add_argument('--schemas', default="./configs/schemas.json")


    # known args used to supply command line args to pytest without raising an error here
    args, _ = parser.parse_known_args()

    # Logging configuration

    log_handler = logging.FileHandler(args.logfile)
    numeric_loglevel = getattr(logging, args.loglevel.upper())
    log_handler.setLevel(numeric_loglevel)

    app.app.logger.addHandler(log_handler)
    app.app.logger.setLevel(numeric_loglevel)

    app.app.config["self"] = "http://{}:{}".format(args.host, args.port)

    # set up db

    define("dbfile", default=args.database)
    candig_dataset_service.orm.init_db()
    db_session = candig_dataset_service.orm.get_session()

    @app.app.teardown_appcontext
    def shutdown_session(exception=None):  # pylint:disable=unused-variable,unused-argument
        """
        Tear down the DB session
        """

        db_session.remove()

    return app, args.port


def configure_app():
    """
    Set up base flask app from Connexion
    App pulled out as global variable to allow import into
    testing files to access application context
    """
    app = connexion.FlaskApp(__name__, server='tornado')

    # api_def = pkg_resources.resource_filename('candig_federation', 'api/federation.yaml')

    api_def = './api/datasets.yaml'

    app.add_api(api_def, strict_validation=True, validate_responses=True)

    return app


app = configure_app()

APPLICATION, PORT = main()

# expose flask app for uwsgi

application = APPLICATION.app

if __name__ == '__main__':
    APPLICATION.app.logger.info("datasets_service running at {}".format(APPLICATION.app.config["self"]))
    APPLICATION.run(port=PORT)
