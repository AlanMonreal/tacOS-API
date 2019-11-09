import OnlineServices
import MySQLdb
from requests import post
from os import getenv
from json import dumps


class Address(object):
    __slots__ = 'track', 'kind', 'line', 'neighborhood', 'city', 'postal',
    'latitude', 'longitude', 'warnings'

    def __init__(self, track, kind, line, neighborhood, city, postal):
        self.track = track
        self.kind = kind
        self.line = line
        self.neighborhood = neighborhood
        self.city = city
        self.postal = postal

    def __str__(self):
        return 'track: %s, kind: %s, warnings: %s'(self.track, self.kind,
                                                   self.warnings)


class Order(object):
    __slots__ = 'track', 'kind', 'service', 'latitude', 'longitude', 'size',
    'weight', 'unit', 'dlat', 'dlng', 'length', 'width', 'height'

    def __init__(self, track, kind, service, latitude, longitude, size=None,
                 weight=None, unit=None, dlat=None, dlng=None, length=None,
                 width=None, height=None):
        self.track = track
        self.kind = kind
        self.service = service
        self.latitude = float(latitude) if latitude else None
        self.longitude = float(longitude) if longitude else None
        self.size = size
        self.weight = weight
        self.unit = unit if unit else None
        self.dlat = float(dlat) if dlat else None
        self.dlng = float(dlng) if dlng else None
        self.length = float(length) if length else None
        self.width = float(width) if width else None
        self.height = float(height) if height else None

    def __str__(self):
        return 'track: %s, kind: %s'(self.track, self.kind)


class Unit(object):
    __slots__ = 'name', 'base', 'capacity', 'specialty'

    def __init__(self, name, base, capacity, specialty=None):
        self.name = name
        self.base = base
        self.capacity = capacity
        self.specialty = specialty if specialty else None


class BaseLocation(object):
    __slots__ = 'name', 'y', 'x'

    def __init__(self, name, y, x):
        self.name = name
        self.y = y
        self.x = x


SHIPMENT_STATUS = {
    'pickup': 2,
    'store': 3,  # Package arrived to station
    'load': 4,  # Package assigned and loaded to unit
    'deliver': 5,
    'error': 7,
    'information': 6
}


# TODO: agregar el precio de los productos individuales
def create_order(dbvars, data, user):
    create_new_order_reg(dbvars, user)
    order_id = get_created_order(dbvars, user)
    insert_order_history(dbvars, user, order_id, data)
    return order_id


def update_order(dbvars, user, order_id, data):
    deactivate_prev_order(dbvars, order_id)
    insert_order_history(dbvars, user, order_id, data)


def finish_order(dbvars, order_id):
    deactivate_prev_order(dbvars, order_id)
    finalize_order(dbvars, order_id)


def create_product(dbvars, data, user_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'INSERT INTO productos (name, price, user_id) VALUES' \
          ' (%s, %s, %s)'
    dbcur.execute(sql, (data['name'], data['price'], user_id))
    dbconn.commit()
    dbcur.close()
    dbconn.close()
    return get_created_product(dbvars, user_id)


def update_product(dbvars, product_id, data):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE productos SET name = %s, price = %s WHERE id = %s'
    dbcur.execute(sql, (data['name'], data['price'], product_id))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def delete_product(dbvars, product_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE productos SET active = 0 WHERE id = %s'
    dbcur.execute(sql, (product_id,))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def create_supply(dbvars, data, user_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'INSERT INTO suministros (name, quantity, price, user_id) VALUES' \
          ' (%s, %s, %s, %s)'
    dbcur.execute(sql, (data['name'], data['quantity'], data['price'], user_id))
    dbconn.commit()
    dbcur.close()
    dbconn.close()
    return get_created_supply(dbvars, user_id)


def update_supply(dbvars, supply_id, data):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE suministros SET name = %s, quantity = %s, price = %s WHERE id = %s'
    dbcur.execute(sql, (data['name'], data['quantity'], data['price'], supply_id))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def delete_supply(dbvars, supply_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE suministros SET active = 0 WHERE id = %s'
    dbcur.execute(sql, (supply_id,))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def create_new_order_reg(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'INSERT INTO ordenes (user_id, total_price) VALUES(%s, 0)'
    dbcur.execute(sql, (user,))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_created_order(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT id FROM ordenes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1'
    dbcur.execute(sql, (user,))
    order = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return order[0][0] if order else None


def get_created_product(dbvars, user_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT id FROM productos WHERE user_id = %s ORDER BY created_at DESC LIMIT 1'
    dbcur.execute(sql, (user_id,))
    product_id = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return product_id[0][0] if product_id else None


def get_created_supply(dbvars, user_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT id FROM suministros WHERE user_id = %s ORDER BY created_at DESC LIMIT 1'
    dbcur.execute(sql, (user_id,))
    supply_id = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return supply_id[0][0] if supply_id else None


def update_order_price(dbvars, order_id):
    total_price = 0
    prices = get_order_price(dbvars, order_id)
    for price in prices:
        total_price += price[0]
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE ordenes SET total_price = %s WHERE id = %s'
    dbcur.execute(sql, (total_price, order_id))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_order_price(dbvars, order_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT total_price FROM historial_ventas WHERE order_id = %s AND active = TRUE'
    dbcur.execute(sql, (order_id,))
    order = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return order if order else None


def get_product_price(dbvars, id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT price FROM productos WHERE id = %s AND active = TRUE'
    dbcur.execute(sql, (id,))
    order = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return order[0][0] if order else None


def get_email(dbvars, token):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT email FROM users WHERE app_token = %s', (token,))
    email = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return email[0][0] if email else None


def update_token(dbvars, username, token):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('UPDATE users SET app_token = %s WHERE email = %s',
                  (token, username))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_user_hash(dbvars, username):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT password FROM users WHERE email = %s', (username,))
    passHash = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return passHash[0][0]


def user_from_token(dbvars, token):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    regs = dbcur.execute('SELECT id FROM users WHERE app_token = %s', (token,))
    unitData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return unitData[0][0] if regs else None


def insert_order_history(dbvars, user, order_id, data):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    insertData = []
    for item in data:
        price = get_product_price(dbvars, item['id']) * item['quantity']
        insertData.append((item['id'], item['quantity'], user, order_id, price))
    sql = 'INSERT INTO historial_ventas (product_id, quantity, user_id,' \
          'order_id, total_price) VALUES(%s, %s, %s, %s, %s)'

    dbcur.executemany(sql, insertData)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def deactivate_prev_order(dbvars, order_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE historial_ventas SET active = FALSE WHERE order_id = %s'
    dbcur.execute(sql, (order_id,))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def finalize_order(dbvars, order_id):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'UPDATE ordenes SET active = 0 WHERE id = %s'
    dbcur.execute(sql, (order_id,))
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_all_products(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT id, name, price FROM productos WHERE user_id = %s AND active = TRUE'
    dbcur.execute(sql, (user,))
    regs = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return regs if regs else None


def get_all_supplies(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT id, name, quantity, price FROM suministros WHERE user_id = %s AND active = TRUE'
    dbcur.execute(sql, (user,))
    regs = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return regs if regs else None


def get_all_orders(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT id, total_price, CAST(created_at AS char(25)) FROM ordenes WHERE user_id = %s AND active = TRUE'
    dbcur.execute(sql, (user,))
    orders = dbcur.fetchall()
    print(orders)

    sql = 'SELECT id, name, price FROM productos WHERE user_id = %s AND active = TRUE'
    dbcur.execute(sql, (user,))
    raw_products = dbcur.fetchall()
    product_list = []
    for rp in raw_products:
        product_list.append(OnlineServices.Product(*rp).__dict__)

    for prod in product_list:
        print(prod)

    sql = 'SELECT order_id, product_id, quantity FROM historial_ventas WHERE user_id = %s AND active = TRUE'
    dbcur.execute(sql, (user,))
    order_products = dbcur.fetchall()
    order_hist_list = []
    for op in order_products:
        order_hist_list.append(OnlineServices.ProdOrder(*op).__dict__)

    for ohl in order_hist_list:
        print(ohl)

    orders_data = []

    for order in orders:
        complete_order = []
        for item in order:
            complete_order.append(item)
        subList = []

        for product in order_hist_list:
            if order[0] == product['order_id']:
                for prod in product_list:
                    if prod['id'] == product['product_id']:
                        subList.append(product)

        complete_order.append(subList)
        orders_data.append(complete_order)
    tuple(orders_data)
    dbcur.close()
    dbconn.close()
    return orders_data if orders_data else None


# ---------------------------------------------------------------------------
def get_base_locations(dbvars):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT name, latitude, longitude FROM base_locations WHERE active=true'
    dbcur.execute(sql)
    baseLocData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    baseLocations = []
    for baseLoc in baseLocData:
        baseLocations.append(BaseLocation(baseLoc[0], float(baseLoc[1]),
                                          float(baseLoc[2])))
    return baseLocations[0]


def get_unit_shipments(dbvars, unit, base):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    # TODO: add int number
    sql = '''SELECT o.id, o.shipment_id as tracking, o.kind,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_latitude
            WHEN o.kind = 'deliver'
            THEN s.destination_latitude
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN {}
            END AS latitude,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_longitude
            WHEN o.kind = 'deliver'
            THEN s.destination_longitude
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN {}
            END AS longitude,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_name
            WHEN o.kind = 'deliver'
            THEN s.destination_name
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN '{}'
            END AS name,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_phone
            WHEN o.kind = 'deliver'
            THEN s.destination_phone
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN NULL
            END AS phone,
            CASE WHEN o.kind = 'pickup'
            THEN CONCAT(IFNULL(s.origin_street,''), ' ', IFNULL(s.origin_ext_number,''))
            WHEN o.kind = 'deliver'
            THEN CONCAT(IFNULL(s.destination_street,''), ' ', IFNULL(s.destination_ext_number,''))
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN NULL
            END AS line,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_district
            WHEN o.kind = 'deliver'
            THEN s.destination_district
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN NULL
            END AS neighborhood,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_city
            WHEN o.kind = 'deliver'
            THEN s.destination_city
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN NULL
            END AS city,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_postal_code
            WHEN o.kind = 'deliver'
            THEN s.destination_postal_code
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN NULL
            END AS postal,
            CASE WHEN o.kind = 'pickup'
            THEN s.origin_reference
            WHEN o.kind = 'deliver'
            THEN s.destination_reference
            WHEN o.kind = 'store' OR o.kind = 'load'
            THEN NULL
            END AS reference,
            s.content, s.weight, s.length, s.width, s.height,
            s.origin_company AS company
            FROM unit_shipments AS o LEFT JOIN shipment_guides AS s
            ON o.shipment_id=s.tracking_number
            WHERE o.unit_id = %s ORDER BY o.sequence'''.format(base.y, base.x,
                                                               base.name)
    dbcur.execute(sql, (unit,))
    unitShipmentData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return unitShipmentData


def update_guide_status(dbvars, tracks, status, msg, user, receiver):
    statusCode = SHIPMENT_STATUS[status]
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    insertData = []
    if status == 'pickup' or status == 'load':
        for track in tracks:
            insertData.append((statusCode, user, track))
    elif status == 'deliver' and receiver:
        for track in tracks:
            insertData.append((statusCode, receiver, track))
    else:
        for track in tracks:
            insertData.append((statusCode, track))
    if status == 'pickup':
        sql = 'UPDATE shipment_guides SET status_id = %s, picked_station_by ='\
              ' %s, assigned_to = NULL WHERE tracking_number = %s'
        dbcur.executemany(sql, insertData)
    elif status == 'load':
        sql = 'UPDATE shipment_guides SET status_id = %s, picked_delivery_by '\
              '= %s WHERE tracking_number = %s'
        dbcur.executemany(sql, insertData)
    elif status == 'deliver' and receiver:
        sql = 'UPDATE shipment_guides SET status_id = %s, destination_'\
              'signature = %s, assigned_to = NULL WHERE tracking_number = %s'
        dbcur.executemany(sql, insertData)
        send_mail(dbvars, tracks)
    else:
        sql = 'UPDATE shipment_guides SET status_id = %s, assigned_to = NULL'\
              ' WHERE tracking_number = %s'
        dbcur.executemany(sql, insertData)
    insertData.clear()
    for track in tracks:
        insertData.append((track, statusCode, msg, user))
    sql = 'INSERT INTO shipment_history (shipment_guide_tracking_number,'\
          ' status_id, description, created_by) VALUES (%s, %s, %s, %s)'
    dbcur.executemany(sql, insertData)
    insertData.clear()
    for track in tracks:
        insertData.append((track,))
        dbcur.executemany('DELETE FROM unit_shipments WHERE shipment_id = %s',
                          insertData)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_assigned_guides(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT tracking_number FROM shipment_guides WHERE assigned_to = %s'\
          ' AND status_id IN (1, 3, 4, 9, 10)'
    dbcur.execute(sql, (user,))
    data = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return data


def getUnitUser(dbvars, unit):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT user_id FROM units WHERE id = %s;', (unit,))
    userData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return userData


def unit_from_token(dbvars, token):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT u.id AS unit FROM users AS a LEFT JOIN units AS u ON'\
          ' u.user_id = a.id WHERE a.app_token = %s'
    regs = dbcur.execute(sql, (token,))
    unitData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return unitData[0][0] if regs else None


def set_guides(dbvars, trackings, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    data = []
    for tracking in trackings:
        data.append((SHIPMENT_STATUS['load'], user, user, tracking))
    sql = 'UPDATE shipment_guides SET status_id = %s, assigned_to = %s,' \
          ' picked_delivery_by = %s WHERE tracking_number = %s'
    dbcur.executemany(sql, data)
    data.clear()
    for tracking in trackings:
        data.append((tracking, SHIPMENT_STATUS['load'],
                    'Package is out for delivery', user))
    sql = 'INSERT INTO shipment_history (shipment_guide_tracking_number,' \
          ' status_id, description, created_by) VALUES (%s, %s, %s, %s)'
    dbcur.executemany(sql, data)
    data.clear()
    for tracking in trackings:
        data.append((tracking,))
    sql = 'DELETE FROM unit_shipments WHERE shipment_id = %s'
    dbcur.executemany(sql, data)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def remove_guide(dbvars, unit, trackings):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    insertData = []
    for tracking in trackings:
        insertData.append((tracking,))
    sql = 'UPDATE shipment_guides SET assigned_to = null WHERE tracking_number = %s'
    dbcur.executemany(sql, insertData)
    insertData.clear()
    for tracking in trackings:
        insertData.append((unit, tracking))
    sql = 'DELETE FROM unit_shipments WHERE unit_id = %s AND shipment_id = %s'
    dbcur.executemany(sql, insertData)
    insertData.clear()
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_role(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT role_id FROM users WHERE id = %s', (user,))
    role = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return role[0][0]


def update_file_name(dbvars, tracks, file, info):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    insertData = []
    for track in tracks:
        insertData.append((track, file, info))
    sql = 'INSERT INTO files (tracking_number, file_path, description)' \
          ' VALUES(%s, %s, %s)'
    dbcur.executemany(sql, insertData)
    dbconn.commit()
    dbcur.close()
    dbconn.close()
