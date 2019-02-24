import requests

# Simple interface to get a location from an IP address
def get_location(ip_addr):
  r = requests.get("http://ip-api.com/json/" + ip_addr)

  if r.status_code != 200:
    return None

  return r.json()

def get_location_str(ip_addr):
  loc = get_location(ip_addr)

  try:
    return loc['city'] + ", " + loc['region'] + ", " + loc['country']

  except:
    return "Location not found."

def get_location_latlon(ip_addr):
  loc = get_location(ip_addr)

  try:
    return (loc['lat'], loc['lon'])
  except:
    return (0, 0)