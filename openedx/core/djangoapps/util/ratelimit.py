"""
Code to get ip from request.
"""


from ipware.ip import get_client_ip


def real_ip(group, request):
    return get_client_ip(request)[0]
