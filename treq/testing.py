"""
Module that has testing utilities that use treq as a library.

This provides a StubTreq object that has the same API as the treq module.
"""
import json
from functools import partial

from twisted.internet.defer import succeed


class StubResponse(object):
    """
    A fake pre-built Response object.  This is only to be used for
    faking responses from :class:`StubTreq`, and is not a full fake of the
    :class:`twisted.web.client.Response` object.
    """
    def __init__(self, code, headers, data=None):
        """
        :param int code: The HTTP status code
        :param dict headers: A headers dictionary
        :param bytes data: The content fo the response
        """
        self.code = code
        self.headers = headers
        # Data is not part of twisted response object - this is used to
        # specify the content of the response
        self._data = data

    def __eq__(self, other):
        """
        Test for equivalence.
        """
        return (
            isinstance(other, self.__class__) and
            self.code == other.code and
            self.headers == other.headers and
            self._data == other._data)

    def __ne__(self, other):
        """
        Test for non-equivalence.
        """
        return not self == other


class ResponseMapping(object):
    """
    An association list of
    `(method, url, <all other treq kwargs as a dictionary>)` as a key mapped
    to :class:`StubResponse` objects.

    Getting the response from request tuple will always return the
    :class:`StubResponse` mapped to it.
    """
    def __init__(self, stubs=None):
        """
        :param iterable stubs:
            the iterable of `(<request-args>, <response>) tuples.
        """
        self.stubs = [] if stubs is None else stubs
        # check to make sure each request only appears once
        for i, item in enumerate(self.stubs):
            for itemagain in self.stubs[i + 1:]:
                if item[0] == itemagain[0]:
                    raise Exception(
                        "Duplicate requests and responses: "
                        "{0!r}:{1!r} and {2!r}:{3!r}"
                        .format(item[0], item[1], itemagain[0], itemagain[1]))

    def __str__(self):
        """
        Return a string representation of this object.
        """
        return 'ResponseMapping (association list): {0}'.format(self.stubs)

    def get_response(self, method, url, **kwargs):
        """
        Return the response mapped to the tuple of `(method, url, kwargs)`.

        :raises: :class:`ValueError` if there is no request mapped.
        """
        for req, resp in self.stubs:
            if req == (method, url, kwargs):
                return resp
        raise ValueError("No response mapped to ({0}, {1}, {2!r}"
                         .format(method, url, kwargs))


class ResponseSequence(object):
    """
    A list of 2-item tuples of
    `(method, url, <all other treq kwargs as a dictionary>)` and
    :class:`StubResponse` objects.

    Getting the response from request tuple will only return ther esponse if
    the `(request, response)` tuple is the first item on the list.
    """
    def __init__(self, stubs=None):
        """
        :param iterable stubs:
            the iterable of `(<request-args>, <response>) tuples.
        """
        self.stubs = [] if stubs is None else stubs

    def __str__(self):
        """
        Return a string representation of this object.
        """
        return 'ResponseSequence: {0}'.format(self.stubs)

    def get_response(self, method, url, **kwargs):
        """
        Return the response mapped to the tuple of `(method, url, kwargs)`.

        :raises: :class:`ValueError` if the request is not the first one in
        the list.
        """
        if len(self.stubs) > 0:
            expected_req, resp = self.stubs[0]
            if expected_req == (method, url, kwargs):
                return resp

        raise ValueError("Not expecting request ({0}, {1}, {2!r}"
                         .format(method, url, kwargs))


class StubTreq(object):
    """
    A stub version of :mod:`treq` that returns canned responses.

    It takes either a :class:`ResponseMapping` or :class:`ResponseSequence`
    that contains expected request arguments mapped to responses that should
     be returned.  The request arguments include the method.

    If a request is made for which there is no stub, a :class:`ValueError` is
    raised.

    :ivar iterable stubs: An iterable of 2-item tuple containing
        (method, url, <all other treq kwargs as a dictionary>) as the first
        item.

        The second item is an iterable of StubResponse objects. Each
        `request` call with same args will return first popped element.

        This iterable functions as an association list. Requests should not
        be in the iterable more than once.  This would be a dictionary
        keyed on the request arguments instead, but the dictionary of
        kwargs is not hashable.
    """
    def __init__(self, stubs):
        """
        :param stubs: the iterable of `(<request-args>, <response>) tuples.
        """
        self.stubs = stubs

    def request(self, method, url, **kwargs):
        """
        Return a result by looking up the arguments in the `reqs` dict.
        The only kwargs we care about are 'headers' and 'data',
        although if other kwargs are passed their keys count as part of the
        request.
        """
        resp = self.stubs.get_response(method, url, **kwargs)
        return succeed(resp)

    def content(self, response):
        """Return a result by taking the data from `response` itself."""
        return succeed(response._data)

    def json_content(self, response):
        """Return :meth:`content` after json-decoding"""
        return self.content(response).addCallback(json.loads)

    def put(self, url, data=None, **kwargs):
        """
        Syntactic sugar for making a PUT request, because the order of the
        params are different than :meth:`request`
        """
        return self.request('PUT', url, data=data, **kwargs)

    def post(self, url, data=None, **kwargs):
        """
        Syntactic sugar for making a POST request, because the order of the
        params are different than :meth:`request`
        """
        return self.request('POST', url, data=data, **kwargs)

    def __getattr__(self, method):
        """
        Syntactic sugar for making head/get/delete requests, because the order
        of parameters is the same as :meth:`request`
        """
        if method in ('get', 'head', 'delete'):
            return partial(self.request, method.upper())
        raise AttributeError("StubTreq has no attribute '{0}'".format(method))

    def __str__(self):
        """
        Return a string represntation of this object.
        """
        return 'StubTreq with {0}'.format(self.stubs)
