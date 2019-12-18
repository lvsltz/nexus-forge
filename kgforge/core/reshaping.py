# 
# Knowledge Graph Forge is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Knowledge Graph Forge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with Knowledge Graph Forge. If not, see <https://www.gnu.org/licenses/>.

from typing import Callable, Dict, Iterator, List, Union

from kgforge.core import Resource
from kgforge.core.commons.attributes import repr_class
from kgforge.core.commons.execution import catch, dispatch
from kgforge.core.conversions.json import as_json


class Reshaper:

    # This class is not intended to be specialized.

    def __init__(self, versioned_id_template: str) -> None:
        self.versioned_id_template: str = versioned_id_template

    def __repr__(self) -> str:
        return repr_class(self)

    @catch
    def reshape(self, data: Union[Resource, List[Resource]], keep: List[str],
                versioned: bool) -> Union[Resource, List[Resource]]:
        # POLICY Resource _last_action and _store_metadata should be None.
        # POLICY Resource _validated and _synchronized should be False.
        return dispatch(data, self._reshape_many, self._reshape_one, keep, versioned)

    def _reshape_many(self, resources: List[Resource], keep: List[str],
                      versioned: bool) -> List[Resource]:
        # Could be optimized in the future.
        return [self._reshape(x, keep, versioned) for x in resources]

    def _reshape_one(self, resource: Resource, keep: List[str], versioned: bool) -> Resource:
        return self._reshape(resource, keep, versioned)

    def _reshape(self, resource: Resource, keep: List[str], versioned: bool) -> Resource:
        # TODO Use as base an implementation of JSONPath for Python. DKE-147.
        levels = [x.split(".", maxsplit=1) for x in keep]
        roots = {x[0] for x in levels}
        new = Resource()
        for root in roots:
            leafs = [x[1] for x in levels if len(x) > 1 and x[0] == root]
            value = getattr(resource, root)
            if isinstance(value, List):
                new_value = self._reshape_many(value, leafs, versioned)
            elif isinstance(value, Resource):
                if leafs:
                    new_value = self._reshape_one(value, leafs, versioned)
                else:
                    attributes = value.__dict__.items()
                    properties = {k: v for k, v in attributes if k not in value._RESERVED}
                    new_value = Resource(**properties)
            else:
                if root == "id" and versioned:
                    new_value = self.versioned_id_template.format(x=resource)
                else:
                    new_value = value
            setattr(new, root, new_value)
        return new


# TODO Use an implementation of JSONPath for Python instead to get values. DKE-147.
def collect_values(data: Union[Resource, List[Resource]],  follow: str,
                   exception: Callable = Exception) -> List[str]:
    def _collect(things: List) -> Iterator[str]:
        for x in things:
            if isinstance(x, Dict):
                for k, v in x.items():
                    if isinstance(v, List):
                        yield from _collect(v)
                    elif isinstance(v, Dict):
                        yield from _collect([v])
                    else:
                        yield v
    try:
        r = Reshaper("")
        reshaped = dispatch(data, r._reshape_many, r._reshape_one, [follow], False)
        jsoned = as_json(reshaped, False, False)
        prepared = jsoned if isinstance(jsoned, List) else [jsoned]
        return list(_collect(prepared))
    except AttributeError:
        raise exception("path to follow is incorrect")