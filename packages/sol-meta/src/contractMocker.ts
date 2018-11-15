import * as S from 'solidity-parser-antlr';

import { makeConstructor, nonAbstractForcer } from './constructor';
import { exposeNode } from './exposer';
import { flattenContract } from './flattener';
import { stubFunction } from './stubber';
import { FunctionScript, scriptFunction } from './scripter';
import { SourceCollection } from './source_reader';
import * as utils from './utils';
import { unparse } from './unparser';

export const mockContractName = (contractName: string) => `${contractName}Mock`;

export interface ContractMockOptions {
    constructors: {
        [parentName: string]: utils.Litteral[];
    };
    scripted: {
        [functionName: string]: FunctionScript[];
    };
}

export function mockContract(
    sources: SourceCollection,
    path: string,
    contractName: string,
    options: ContractMockOptions,
): S.SourceUnit {
    const sourceInfo = sources[path];

    // Flatten target contract, this collapses the inheritane hierarchy
    if (!(contractName in sourceInfo.contracts)) {
        throw new Error(`Could not find contract ${contractName} in "${path}".`);
    }
    const [flat, parents] = flattenContract(sourceInfo.contracts[contractName], name => {
        if (!(name in sourceInfo.scope)) {
            console.log(Object.keys(sourceInfo.scope));
            throw new Error(`Contract ${name} not in scope of ${path}.`);
        }
        return sourceInfo.scope[name];
    });

    // Find all constructors that require arguments
    // TODO: Ignore constructors already called from other constructors
    const constructors = parents
        .filter(({ subNodes }) =>
            subNodes.some(
                node =>
                    node.type === S.NodeType.FunctionDefinition &&
                    node.isConstructor &&
                    node.parameters.parameters.length > 0,
            ),
        )
        .map(({ name }) => name);

    // Check that we have arguments for all constructors that require them
    constructors.forEach(name => {
        if (!(name in options.constructors)) {
            throw new Error(`No arguments for constructor ${name} in ${contractName}.`);
        }
    });

    // Find all abstract functions
    // TODO: Public member variables generate implicit getter functions that can satisfy an abstract.
    const abstracts = flat.subNodes.filter(
        node => node.type === S.NodeType.FunctionDefinition && node.body === null,
    ) as S.FunctionDefinition[];

    // Separated in scripted and mocked functions
    const scripted = abstracts.filter(({ name }) => name && name in options.scripted);
    const mocked = abstracts.filter(({ name }) => name && !(name in options.scripted));

    // Create mock contract
    const mock: S.ContractDefinition = {
        type: S.NodeType.ContractDefinition,
        kind: S.ContractKind.Contract,
        name: mockContractName(contractName),

        // Inherit from source contract
        baseContracts: [
            {
                type: S.NodeType.InheritanceSpecifier,
                baseName: utils.userType(contractName),
            },
        ],
        subNodes: [
            // Call parent constructors
            makeConstructor(utils.objectFilter(options.constructors, (key, _) => constructors.includes(key))),

            // Expose things marked `internal`
            ...utils.flatMap(flat.subNodes, exposeNode),

            // Compile-time specified scripted functions
            ...scripted.map(func => scriptFunction(func, options.scripted[func.name || ''])),

            // Mock all remaining abstract functions
            ...utils.flatMap(mocked, stubFunction),
        ],
    };

    // Create source file
    return {
        type: S.NodeType.SourceUnit,
        children: [
            // Copy over pragmas from the source file
            ...sources[path].parsed.children.filter(({ type }) => type === S.NodeType.PragmaDirective),

            // Add an import to include the source file
            // TODO: Make relative
            {
                type: S.NodeType.ImportDirective,
                path,
                symbolAliases: null,
            },

            // Include our mock contract
            mock,

            // Add a utility contract to force an abstract mock contract into a compile error.
            nonAbstractForcer(mockContractName(contractName)),
        ],
    };
}
