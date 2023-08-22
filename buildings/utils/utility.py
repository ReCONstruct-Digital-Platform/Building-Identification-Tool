import hmac
import hashlib
from django.http import QueryDict


def print_query_dict(data: QueryDict):
    print('QueryDict: {')
    for l in data.lists():
        print(f'\t{l[0]}: {l[1]},')
    print('}')


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
