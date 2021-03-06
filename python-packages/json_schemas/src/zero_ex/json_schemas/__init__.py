"""JSON schemas and associated utilities.

Validating a 0x Order
---------------------

Here is an example on how to validate a 0x order.

>>> from zero_ex.json_schemas import assert_valid
>>> example_order = {
...     'makerAddress': '0x5409ed021d9299bf6814279a6a1411a7e866a631',
...     'takerAddress': '0x0000000000000000000000000000000000000000',
...     'senderAddress': '0x0000000000000000000000000000000000000000',
...     'exchangeAddress': '0x4f833a24e1f95d70f028921e27040ca56e09ab0b',
...     'feeRecipientAddress':
...         '0x0000000000000000000000000000000000000000',
...     'makerAssetData': '0xf47261b0000000000000000000000000'
...         'c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
...     'takerAssetData': '0xf47261b0000000000000000000000000'
...         'e41d2489571d322189246dafa5ebde1f4699f498',
...     'salt': 123456789,
...     'makerFee': 0,
...     'takerFee': 0,
...     'makerAssetAmount': 1000000000000000000,
...     'takerAssetAmount': 500000000000000000000,
...     'expirationTimeSeconds': 1553553429
... }
>>> assert_valid(example_order, "/orderSchema")
"""

from os import path
import json
from typing import Mapping

from pkg_resources import resource_string
import jsonschema
from stringcase import snakecase


class _LocalRefResolver(jsonschema.RefResolver):
    """Resolve package-local JSON schema id's."""

    def __init__(self):
        """Initialize a new instance."""
        jsonschema.RefResolver.__init__(self, "", "")

    @staticmethod
    def resolve_from_url(url: str) -> str:
        """Resolve the given URL.

        :param url: a string representing the URL of the JSON schema to fetch.
        :returns: a string representing the deserialized JSON schema
        :raises jsonschema.ValidationError: when the resource associated with
                   `url` does not exist.
        """
        ref = url.replace("file://", "")
        return json.loads(
            resource_string(
                "zero_ex.json_schemas",
                f"schemas/{snakecase(ref.lstrip('/'))}.json",
            )
        )


# Instantiate the `_LocalRefResolver()` only once so that `assert_valid()` can
# perform multiple schema validations without reading from disk the schema
# every time.
_LOCAL_RESOLVER = _LocalRefResolver()


def assert_valid(data: Mapping, schema_id: str) -> None:
    """Validate the given `data` against the specified `schema`.

    :param data: Python dictionary to be validated as a JSON object.
    :param schema_id: id property of the JSON schema to validate against.  Must
        be one of those listed in `the 0x JSON schema files
        <https://github.com/0xProject/0x-monorepo/tree/development/packages/json-schemas/schemas>`_.

    Raises an exception if validation fails.

    >>> assert_valid(
    ...     {'v': 27, 'r': '0x'+'f'*64, 's': '0x'+'f'*64},
    ...     '/ecSignatureSchema',
    ... )
    """
    # noqa

    _, schema = _LOCAL_RESOLVER.resolve(schema_id)
    jsonschema.validate(data, schema, resolver=_LOCAL_RESOLVER)


def assert_valid_json(data: str, schema_id: str) -> None:
    """Validate the given `data` against the specified `schema`.

    :param data: JSON string to be validated.
    :param schema_id: id property of the JSON schema to validate against.  Must
        be one of those listed in `the 0x JSON schema files
        <https://github.com/0xProject/0x-monorepo/tree/development/packages/json-schemas/schemas>`_.

    Raises an exception if validation fails.

    >>> assert_valid_json(
    ...     r'''{
    ...         "v": 27,
    ...         "r": "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    ...         "s": "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    ...     }''',
    ...     '/ecSignatureSchema',
    ... )
    """  # noqa: E501 (line too long)
    assert_valid(json.loads(data), schema_id)
