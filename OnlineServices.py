#!/usr/bin/env python3

import queries
import auth
from os import getenv
from urllib.parse import urlparse


class Order():
    def __init__(self, iden, tracking, kind, y, x, name, phone, line,
                 neighborhood, city, postal, reference, content, weight,
                 length, width, height, company):
        self.iden = iden
        self.tracking = tracking
        self.kind = kind
        self.y = float(y)  # if y else None
        self.x = float(x)  # if x else None
        self.name = name
        self.phone = phone
        self.company = company
        self.address = {'line': line, 'neighborhood': neighborhood,
                        'city': city, 'postal': postal, 'reference': reference}
        self.package = {'content': content, 'weight': weight, 'length': length,
                        'width': width, 'height': height}


class AssignedGuide():
    def __init__(self, tracking):
        self.tracking = tracking if tracking else None


class OnlineServices:
    def __init__(self):

        dbvars = urlparse(getenv('DBSTRING'))
        self.db = {
            'host': dbvars.hostname,
            'user': dbvars.username,
            'pass': dbvars.password,
            'name': dbvars.path[1:]
        }

    def validate_user(self, token):
        user = queries.user_from_token(self.db, token)
        return user if user else False

    def login(self, username, password):
        passhash = queries.get_user_hash(self.db, username)
        token = auth.validate_login(password, passhash)
        if token:
            queries.update_token(self.db, username, token)
            email = queries.get_email(self.db, token)
            response = {'token': token, 'email': email}
        return response if token else None

    def create_order(self, token, data):
        user = queries.user_from_token(self.db, token)
        order_id = queries.create_order(self.db, data, user)
        queries.update_order_price(self.db, order_id)
        return order_id

    def update_order(self, token, order_id, data):
        user = queries.user_from_token(self.db, token)
        queries.update_order(self.db, user, order_id, data)
        queries.update_order_price(self.db, order_id)
        return True

    def finish_order(self, order_id):
        queries.finish_order(self.db, order_id)
        return True

    def create_product(self, token, data):
        user = queries.user_from_token(self.db, token)
        product_id = queries.create_product(self.db, data, user)
        return product_id

    def update_product(self, product_id, data):
        queries.update_product(self.db, product_id, data)
        return True

    def delete_product(self, product_id):
        queries.delete_product(self.db, product_id)
        return True

    def create_supply(self, token, data):
        user = queries.user_from_token(self.db, token)
        supply_id = queries.create_supply(self.db, data, user)
        return supply_id

    def update_supply(self, supply_id, data):
        queries.update_supply(self.db, supply_id, data)
        return True

    def delete_supply(self, supply_id):
        queries.delete_supply(self.db, supply_id)
        return True
