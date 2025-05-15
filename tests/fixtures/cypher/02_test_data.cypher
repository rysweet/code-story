// Test Data Generation for Integration Tests
// This creates a minimal but useful codebase structure for testing

// First clear any existing test data
MATCH (n) DETACH DELETE n;

// Create directory structure
CREATE (root:Directory {
  name: 'src',
  path: '/test/repo/src',
  created_at: datetime()
});

// Create src/core directory
CREATE (core:Directory {
  name: 'core',
  path: '/test/repo/src/core',
  created_at: datetime()
});

// Create src/utils directory
CREATE (utils:Directory {
  name: 'utils',
  path: '/test/repo/src/utils',
  created_at: datetime()
});

// Create relationships between directories
MATCH (root:Directory {path: '/test/repo/src'})
MATCH (core:Directory {path: '/test/repo/src/core'})
CREATE (root)-[:CONTAINS]->(core);

MATCH (root:Directory {path: '/test/repo/src'})
MATCH (utils:Directory {path: '/test/repo/src/utils'})
CREATE (root)-[:CONTAINS]->(utils);

// Create a repository node
CREATE (r:Repository {
  name: 'test-repo',
  path: '/test/repo',
  description: 'Test repository for integration tests',
  created_at: datetime()
});

// Link repository to root directory
MATCH (r:Repository {name: 'test-repo'})
MATCH (d:Directory {path: '/test/repo/src'})
CREATE (r)-[:CONTAINS]->(d);

// Create a few Python files
MATCH (core:Directory {path: '/test/repo/src/core'})
CREATE (init_file:File {
  name: '__init__.py',
  path: '/test/repo/src/core/__init__.py',
  language: 'Python',
  content: '"""Core module for the test repository."""\n\nfrom .base import BaseClass\n',
  size: 55,
  created_at: datetime(),
  summary: 'Core module initialization file that imports BaseClass.'
})
CREATE (core)-[:CONTAINS]->(init_file);

MATCH (core:Directory {path: '/test/repo/src/core'})
CREATE (base_file:File {
  name: 'base.py',
  path: '/test/repo/src/core/base.py',
  language: 'Python',
  content: '"""Base classes for the core module."""\n\nclass BaseClass:\n    """Base class for all core classes."""\n\n    def __init__(self, name):\n        """Initialize with a name.\n\n        Args:\n            name: The name of the instance\n        """\n        self.name = name\n\n    def get_name(self):\n        """Return the name of the instance.\n\n        Returns:\n            str: The name\n        """\n        return self.name\n',
  size: 335,
  created_at: datetime(),
  summary: 'Defines BaseClass with name property and getter method.'
})
CREATE (core)-[:CONTAINS]->(base_file);

MATCH (utils:Directory {path: '/test/repo/src/utils'})
CREATE (utils_file:File {
  name: 'string_utils.py',
  path: '/test/repo/src/utils/string_utils.py',
  language: 'Python',
  content: '"""String utility functions."""\n\ndef normalize_string(s):\n    """Normalize a string by trimming and lowercasing.\n\n    Args:\n        s: The string to normalize\n\n    Returns:\n        str: The normalized string\n    """\n    return s.strip().lower()\n\ndef concat_strings(strings, separator=" "):\n    """Concatenate strings with a separator.\n\n    Args:\n        strings: List of strings to concatenate\n        separator: Separator to use between strings\n\n    Returns:\n        str: The concatenated string\n    """\n    return separator.join(strings)\n',
  size: 467,
  created_at: datetime(),
  summary: 'Utility functions for string manipulation including normalization and concatenation.'
})
CREATE (utils)-[:CONTAINS]->(utils_file);

// Create class and function nodes
MATCH (base_file:File {path: '/test/repo/src/core/base.py'})
CREATE (base_class:Class {
  id: 'core.base.BaseClass',
  name: 'BaseClass',
  file_path: '/test/repo/src/core/base.py',
  docstring: 'Base class for all core classes.',
  line_start: 3,
  line_end: 23,
  summary: 'Base class that provides a common name property and getter',
  created_at: datetime()
})
CREATE (base_file)-[:CONTAINS]->(base_class);

MATCH (base_class:Class {id: 'core.base.BaseClass'})
CREATE (init_method:Function {
  id: 'core.base.BaseClass.__init__',
  name: '__init__',
  file_path: '/test/repo/src/core/base.py',
  docstring: 'Initialize with a name.\n\nArgs:\n    name: The name of the instance',
  parameters: ['self', 'name'],
  return_type: 'None',
  line_start: 6,
  line_end: 12,
  summary: 'Constructor that sets the name property',
  created_at: datetime()
})
CREATE (base_class)-[:CONTAINS]->(init_method);

MATCH (base_class:Class {id: 'core.base.BaseClass'})
CREATE (get_name_method:Function {
  id: 'core.base.BaseClass.get_name',
  name: 'get_name',
  file_path: '/test/repo/src/core/base.py',
  docstring: 'Return the name of the instance.\n\nReturns:\n    str: The name',
  parameters: ['self'],
  return_type: 'str',
  line_start: 14,
  line_end: 21,
  summary: 'Getter method that returns the name property',
  created_at: datetime()
})
CREATE (base_class)-[:CONTAINS]->(get_name_method);

// Create function nodes for utility functions
MATCH (utils_file:File {path: '/test/repo/src/utils/string_utils.py'})
CREATE (normalize_fn:Function {
  id: 'utils.string_utils.normalize_string',
  name: 'normalize_string',
  file_path: '/test/repo/src/utils/string_utils.py',
  docstring: 'Normalize a string by trimming and lowercasing.\n\nArgs:\n    s: The string to normalize\n\nReturns:\n    str: The normalized string',
  parameters: ['s'],
  return_type: 'str',
  line_start: 3,
  line_end: 13,
  summary: 'Normalizes strings by trimming whitespace and converting to lowercase',
  created_at: datetime()
})
CREATE (utils_file)-[:CONTAINS]->(normalize_fn);

MATCH (utils_file:File {path: '/test/repo/src/utils/string_utils.py'})
CREATE (concat_fn:Function {
  id: 'utils.string_utils.concat_strings',
  name: 'concat_strings',
  file_path: '/test/repo/src/utils/string_utils.py',
  docstring: 'Concatenate strings with a separator.\n\nArgs:\n    strings: List of strings to concatenate\n    separator: Separator to use between strings\n\nReturns:\n    str: The concatenated string',
  parameters: ['strings', 'separator=" "'],
  return_type: 'str',
  line_start: 15,
  line_end: 26,
  summary: 'Joins multiple strings using a specified separator (space by default)',
  created_at: datetime()
})
CREATE (utils_file)-[:CONTAINS]->(concat_fn);

// Create some relationships between functions (dependencies)
MATCH (normalize_fn:Function {id: 'utils.string_utils.normalize_string'})
MATCH (get_name_method:Function {id: 'core.base.BaseClass.get_name'})
CREATE (normalize_fn)-[:CALLS {count: 1}]->(get_name_method);

MATCH (concat_fn:Function {id: 'utils.string_utils.concat_strings'})
MATCH (normalize_fn:Function {id: 'utils.string_utils.normalize_string'})
CREATE (concat_fn)-[:CALLS {count: 2}]->(normalize_fn);

// Create modules
CREATE (core_module:Module {
  id: 'core',
  name: 'core',
  path: '/test/repo/src/core',
  summary: 'Core module containing base classes and functionality',
  created_at: datetime()
});

CREATE (utils_module:Module {
  id: 'utils',
  name: 'utils',
  path: '/test/repo/src/utils',
  summary: 'Utility functions for common operations',
  created_at: datetime()
});

// Create module relationships
MATCH (core:Directory {path: '/test/repo/src/core'})
MATCH (core_module:Module {id: 'core'})
CREATE (core)-[:REPRESENTS]->(core_module);

MATCH (utils:Directory {path: '/test/repo/src/utils'})
MATCH (utils_module:Module {id: 'utils'})
CREATE (utils)-[:REPRESENTS]->(utils_module);

// Create module imports
MATCH (utils_module:Module {id: 'utils'})
MATCH (core_module:Module {id: 'core'})
CREATE (utils_module)-[:IMPORTS]->(core_module);

RETURN 'Test data created successfully' as status;