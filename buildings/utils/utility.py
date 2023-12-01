import os
import hmac
import base64
import zipfile
import hashlib
import requests
import psycopg2
import traceback
from tqdm import tqdm
from pathlib import Path
import urllib.parse as urlparse
from django.http import QueryDict


def print_query_dict(data: QueryDict):
    print('QueryDict: {')
    for l in data.lists():
        print(f'\t{l[0]}: {l[1]},')
    print('}')


def split_list_in_n(array, n):
    """ Split up a list in n lists evenly size chuncks """
    ret = []
    start = 0
    for i in range(n):
        stop = start + len(array[i::n])
        ret.append({
            'id': i,
            'data': array[start:stop]
        })
        start = stop
    return ret


def get_DB_conn(connection_string, dict_cursor=True):
    conn = psycopg2.connect(connection_string)
    if dict_cursor:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor()
    return conn, cursor


def verify_github_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.
    
    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        return False
    
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        return False
    
    return True


def sizeof_fmt(num, suffix="B"):
    """
    Human readable sizes in bytes
    https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
    """
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.2f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.2f}Yi{suffix}"


def download_file(url, data_folder, unzip=False):
    """
    Downloads large zipfile and unzips it
    """
    filename = Path(data_folder) / Path(url).name

    r = requests.get(url, stream=True)
    total_size= int(r.headers.get('content-length', 0))

    if r.status_code == 200:
        with open(filename, 'wb') as f, tqdm(
            desc=f'Downloading {Path(url).name}',
            total=total_size, 
            unit='iB', 
            unit_scale=True, 
            unit_divisor=1024
        ) as bar:
            for chunk in r:
                size = f.write(chunk)
                bar.update(size)

        # Optionally unzip the file
        if unzip:
            try:
                with zipfile.ZipFile(filename, "r") as zf:
                    for member in tqdm(zf.infolist(), desc=f'Extracting into {data_folder}'):
                        zf.extract(member, data_folder)
                        
                # Remove the zip file after extraction
                os.remove(filename)
            except:
                print(traceback.format_exc())
                exit(1)
    else:
        raise Exception(f'ERROR: Status {r.status_code} unable to retrieve data')


# From google maps docs
def sign_url(input_url=None, secret=None):
    """ Sign a request URL with a URL signing secret.
      Usage:
      from urlsigner import sign_url
      signed_url = sign_url(input_url=my_url, secret=SECRET)
      Args:
      input_url - The URL to sign
      secret    - Your URL signing secret
      Returns:
      The signed request URL
  """

    if not input_url or not secret:
        raise Exception("Both input_url and secret are required")

    url = urlparse.urlparse(input_url)

    # We only need to sign the path+query part of the string
    url_to_sign = url.path + "?" + url.query

    # Decode the private key into its binary format
    # We need to decode the URL-encoded private key
    decoded_key = base64.urlsafe_b64decode(secret)

    # Create a signature using the private key and the URL-encoded
    # string using HMAC SHA1. This signature will be binary.
    signature = hmac.new(decoded_key, str.encode(url_to_sign), hashlib.sha1)

    # Encode the binary signature into base64 for use within a URL
    encoded_signature = base64.urlsafe_b64encode(signature.digest())

    original_url = url.scheme + "://" + url.netloc + url.path + "?" + url.query

    # Return signed URL
    return original_url + "&signature=" + encoded_signature.decode()
