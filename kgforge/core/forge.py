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

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import yaml
from pandas import DataFrame

from kgforge.core import Resource
from kgforge.core.archetypes import Mapping, Model, Resolver, Store
from kgforge.core.commons.actions import LazyAction
from kgforge.core.commons.dictionaries import with_defaults
from kgforge.core.commons.exceptions import ResolvingError
from kgforge.core.commons.execution import catch
from kgforge.core.commons.imports import import_class
from kgforge.core.commons.strategies import ResolvingStrategy
from kgforge.core.conversions.dataframe import as_dataframe, from_dataframe
from kgforge.core.conversions.json import as_json, from_json
from kgforge.core.conversions.jsonld import as_jsonld, from_jsonld
from kgforge.core.conversions.triples import as_triples, from_triples
from kgforge.core.reshaping import Reshaper
from kgforge.core.wrappings.paths import PathsWrapper, wrap_paths
from kgforge.specializations.mappings import DictionaryMapping


class KnowledgeGraphForge:

    # POLICY Class name should be imported in the corresponding module __init__.py.

    # No catching of exceptions so that no incomplete instance is created if an error occurs.
    # This is a best practice in Python for __init__().
    def __init__(self, configuration: Union[str, Dict], **kwargs) -> None:

        # FIXME To be refactored while applying the mapping API refactoring. DKE-104.

        # Required minimal configuration: name for Model and Store, origin and source for Model.
        # Keyword arguments could be used to override the configuration provided for the Store.
        #
        # The configuration could be provided either as:
        #
        #   - A path to a YAML file with the following structure.
        #     Class name could be provided in three formats:
        #       * 'SomeClass',
        #       * 'SomeClass from package.module',
        #       * 'SomeClass from package.module.file'.
        #     When the class is from this package, the first is used. Otherwise, the two others.
        #     Values using braces with something inside should be quoted with double quotes.
        #     See demo-forge.yml in kgforge/examples/configurations/ for an example.
        #
        # Model:
        #   name: <a class name of a Model>
        #   origin: <'directory', 'url', or 'store'>
        #   source: <a directory path, an URL, or the class name of a Store>
        #   bucket: <when 'origin' is 'store', a Store bucket>
        #   endpoint: <when 'origin' is 'store', a Store endpoint, default to Store:endpoint>
        #   token: <when 'origin' is 'store', a Store token, default to Store:token>
        #
        # Store:
        #   name: <a class name of a Store>
        #   endpoint: <an URL>
        #   bucket: <a bucket as a string>
        #   token: <a token as a string>
        #   versioned_id_template: <a string template using 'x' to access resource fields>
        #   file_resource_mapping: <an Hjson string, a file path, or an URL>
        #
        # Resolvers:
        #   <scope>:
        #     - resolver: <a class name of a Resolver>
        #       origin: <'directory', 'web_service', or 'store'>
        #       source: <a directory path, a web service endpoint, or the class name of a Store>
        #       targets:
        #         - identifier: <a name, or an IRI>
        #           bucket: <a file name, an URL path, or a Store bucket>
        #       result_resource_mapping: <an Hjson string, a file path, or an URL>
        #       endpoint: <when 'origin' is 'store', a Store endpoint, default to Store:endpoint>
        #       token: <when 'origin' is 'store', a Store token, default to Store:token>
        #
        # Formatters:
        #   identifier: <a string template with replacement fields delimited by braces, i.e. '{}'>
        #
        #   - A Python dictionary with the following structure.
        #
        # {
        #     "Model": {
        #         "name": <str>,
        #         "origin": <str>,
        #         "source": <str>,
        #         "bucket": <str>,
        #         "endpoint": <str>,
        #         "token": <str>,
        #     },
        #     "Store": {
        #         "name": <str>,
        #         "endpoint": <str>,
        #         "bucket": <str>,
        #         "token": <str>,
        #         "versioned_id_template": <str>,
        #         "file_resource_mapping": <str>,
        #     },
        #     "Resolvers": {
        #         "<scope>": [
        #             {
        #                 "resolver": <str>,
        #                 "origin": <str>,
        #                 "source": <str>,
        #                 "targets": [
        #                     {
        #                         "identifier": <str>,
        #                         "bucket": <str>,
        #                     },
        #                     ...,
        #                 ],
        #                 "result_resource_mapping": <str>,
        #                 "endpoint": <str>,
        #                 "token": <str>,
        #             },
        #             ...,
        #         ],
        #     },
        #     "Formatters": {
        #         "<name>": <str>,
        #         ...,
        #     },
        # }

        if isinstance(configuration, str):
            with Path(configuration).open(encoding="utf-8") as f:
                config = yaml.safe_load(f)
        else:
            config = deepcopy(configuration)

        # Store.

        store_config = config.pop("Store")
        store_config.update(kwargs)
        store_name = store_config.pop("name")
        store = import_class(store_name, "stores")
        self._store: Store = store(**store_config)

        # Model.

        model_config = config.pop("Model")
        if model_config["origin"] == "store":
            with_defaults(model_config, store_config, "name", ["endpoint", "token"])
        model_name = model_config.pop("name")
        model = import_class(model_name, "models")
        self._model: Model = model(**model_config)

        # Resolvers.

        resolvers_config = config.pop("Resolvers", None)
        # Format: Optional[Dict[scope_name, Dict[resolver_name, Resolver]]].
        self._resolvers: Optional[Dict[str, Dict[str, Resolver]]] = prepare_resolvers(
            resolvers_config, store_config) if resolvers_config else None

        # Formatters.

        self._formatters: Optional[Dict[str, str]] = config.pop("Formatters", None)

    # Modeling User Interface.

    @catch
    def prefixes(self) -> Dict[str, str]:
        return self._model.prefixes()

    @catch
    def types(self) -> List[str]:
        return self._model.types()

    @catch
    def template(self, type: str, only_required: bool = False, output: str = "hjson"
                 ) -> Optional[Dict]:
        return self._model.template(type, only_required, output)

    # No @catch because the error handling is done by execution.run().
    def validate(self, data: Union[Resource, List[Resource]],
                 execute_actions_before: bool = False) -> None:
        self._model.validate(data, execute_actions_before)

    # Resolving User Interface.

    @catch
    def resolve(self, text: str, scope: Optional[str] = None, resolver: Optional[str] = None,
                target: Optional[str] = None, type: Optional[str] = None,
                strategy: ResolvingStrategy = ResolvingStrategy.BEST_MATCH
                ) -> Optional[Union[Resource, List[Resource]]]:
        if self._resolvers is not None:
            if scope is not None:
                if resolver is not None:
                    rov = self._resolvers[scope][resolver]
                else:
                    scope_resolvers = list(self._resolvers[scope].values())
                    if len(scope_resolvers) == 1:
                        rov = scope_resolvers[0]
                    else:
                        raise ResolvingError("resolver name should be specified")
            else:
                scopes_resolvers = list(self._resolvers.values())
                if resolver is not None:
                    if len(self._resolvers) == 1:
                        rov = scopes_resolvers[0][resolver]
                    else:
                        raise ResolvingError("resolving scope should be specified")
                else:
                    if len(self._resolvers) == 1 and len(scopes_resolvers[0]) == 1:
                        rov = list(scopes_resolvers[0].values())[0]
                    else:
                        raise ResolvingError("resolving scope or resolver name should be"
                                             "specified")
            return rov.resolve(text, target, type, strategy)
        else:
            raise ResolvingError("no resolvers have been configured")

    # Formatting User Interface.

    @catch
    def format(self, what: str, *args) -> str:
        return self._formatters[what].format(*args)

    # Mapping User Interface.

    # FIXME To be refactored while applying the mapping API refactoring. DKE-104.
    @catch
    def mappings(self, source: str) -> Dict[str, List[str]]:
        return self._model.mappings(source)

    # FIXME To be refactored while applying the mapping API refactoring. DKE-104.
    @catch
    def mapping(self, type: str, source: str,
                mapping_type: Callable = DictionaryMapping) -> Mapping:
        return self._model.mapping(type, source, mapping_type)

    @catch
    def map(self, data: Any, mapping: Union[Mapping, List[Mapping]], mapper: Callable,
            na: Union[Any, List[Any]] = None) -> Union[Resource, List[Resource]]:
        return mapper(self).map(data, mapping, na)

    # Reshaping User Interface.

    @catch
    def reshape(self, data: Union[Resource, List[Resource]], keep: List[str],
                versioned: bool = False) -> Union[Resource, List[Resource]]:
        return Reshaper(self._store.versioned_id_template).reshape(data, keep, versioned)

    # Querying User Interface.

    @catch
    def retrieve(self, id: str, version: Optional[Union[int, str]] = None) -> Resource:
        return self._store.retrieve(id, version)

    @catch
    def paths(self, type: str) -> PathsWrapper:
        template = self._model.template(type, False, "dict")
        return wrap_paths(template)

    @catch
    def search(self, *filters, **params) -> List[Resource]:
        resolvers = list(self._resolvers.values()) if self._resolvers is not None else None
        return self._store.search(resolvers, *filters, **params)

    @catch
    def sparql(self, query: str) -> List[Resource]:
        prefixes = self._model.prefixes()
        return self._store.sparql(prefixes, query)

    @catch
    def download(self, data: Union[Resource, List[Resource]], follow: str, path: str) -> None:
        # path: DirPath.
        self._store.download(data, follow, path)

    # Storing User Interface.

    # No @catch because the error handling is done by execution.run().
    def register(self, data: Union[Resource, List[Resource]]) -> None:
        self._store.register(data)

    # No @catch because the error handling is done by execution.run().
    def update(self, data: Union[Resource, List[Resource]]) -> None:
        self._store.update(data)

    # No @catch because the error handling is done by execution.run().
    def deprecate(self, data: Union[Resource, List[Resource]]) -> None:
        self._store.deprecate(data)

    # Versioning User Interface.

    # No @catch because the error handling is done by execution.run().
    def tag(self, data: Union[Resource, List[Resource]], value: str) -> None:
        self._store.tag(data, value)

    # No @catch because the error handling is done by execution.run().
    def freeze(self, data: Union[Resource, List[Resource]]) -> None:
        self._store.freeze(data)

    # Files Handling User Interface.

    @catch
    def attach(self, path: str) -> LazyAction:
        # path: Union[FilePath, DirPath].
        return LazyAction(self._store.upload, path)

    # Converting User Interface.

    @staticmethod
    @catch
    def as_json(data: Union[Resource, List[Resource]], expanded: bool = False,
                store_metadata: bool = False) -> Union[Dict, List[Dict]]:
        return as_json(data, expanded, store_metadata)

    @staticmethod
    @catch
    def as_jsonld(data: Union[Resource, List[Resource]], compacted: bool = True,
                  store_metadata: bool = False) -> Union[Dict, List[Dict]]:
        return as_jsonld(data, compacted, store_metadata)

    # FIXME To be refactored after the introduction of as_graph(), as_rdf() and as_triplets().
    #  DKE-131, DKE-142, DKE-132.
    @staticmethod
    @catch
    def as_triples(data: Union[Resource, List[Resource]],
                   store_metadata: bool = False) -> List[Tuple[str, str, str]]:
        return as_triples(data, store_metadata)

    @staticmethod
    @catch
    def as_dataframe(data: List[Resource], na: Union[Any, List[Any]] = [None], nesting: str = ".",
                     expanded: bool = False, store_metadata: bool = False) -> DataFrame:
        return as_dataframe(data, na, nesting, expanded, store_metadata)

    @staticmethod
    @catch
    def from_json(data: Union[Dict, List[Dict]], na: Union[Any, List[Any]] = None
                  ) -> Union[Resource, List[Resource]]:
        return from_json(data, na)

    @staticmethod
    @catch
    def from_jsonld(data: Union[Dict, List[Dict]]) -> Union[Resource, List[Resource]]:
        return from_jsonld(data)

    @staticmethod
    @catch
    def from_triples(data: List[Tuple[str, str, str]]) -> Union[Resource, List[Resource]]:
        return from_triples(data)

    @staticmethod
    @catch
    def from_dataframe(data: DataFrame, na: Union[Any, List[Any]] = np.nan, nesting: str = "."
                       ) -> Union[Resource, List[Resource]]:
        return from_dataframe(data, na, nesting)


def prepare_resolvers(config: Dict, store_config: Dict) -> Dict[str, Dict[str, Resolver]]:
    return {scope: dict(prepare_resolver(x, store_config) for x in configs)
            for scope, configs in config.items()}


def prepare_resolver(config: Dict, store_config: Dict) -> Tuple[str, Resolver]:
    if config["origin"] == "store":
        with_defaults(config, store_config, "name", ["endpoint", "token"])
    resolver_name = config.pop("resolver")
    resolver = import_class(resolver_name, "resolvers")
    return resolver.__name__, resolver(**config)
