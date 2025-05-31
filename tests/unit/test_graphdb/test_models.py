"""Tests for graph database models."""

from datetime import datetime

from codestory.graphdb.models import (
    BaseNode,
    BaseRelationship,
    CallsRelationship,
    ClassNode,
    ContainsRelationship,
    DirectoryNode,
    DocumentationNode,
    DocumentedByRelationship,
    FileNode,
    FunctionNode,
    ImportsRelationship,
    InheritsFromRelationship,
    MethodNode,
    ModuleNode,
    NodeType,
    RelationshipType,
    SummarizedByRelationship,
    SummaryNode,
)


def test_node_type_enum() -> None:
    """Test NodeType enumeration."""
    assert NodeType.FILE == "File"
    assert NodeType.DIRECTORY == "Directory"
    assert NodeType.CLASS == "Class"
    assert NodeType.FUNCTION == "Function"
    assert NodeType.METHOD == "Method"
    assert NodeType.MODULE == "Module"
    assert NodeType.SUMMARY == "Summary"
    assert NodeType.DOCUMENTATION == "Documentation"


def test_relationship_type_enum() -> None:
    """Test RelationshipType enumeration."""
    assert RelationshipType.CONTAINS == "CONTAINS"
    assert RelationshipType.IMPORTS == "IMPORTS"
    assert RelationshipType.CALLS == "CALLS"
    assert RelationshipType.INHERITS_FROM == "INHERITS_FROM"
    assert RelationshipType.DOCUMENTED_BY == "DOCUMENTED_BY"
    assert RelationshipType.SUMMARIZED_BY == "SUMMARIZED_BY"


def test_base_node() -> None:
    """Test BaseNode model."""
    # Create with minimal args
    node = BaseNode()
    assert node.id is None
    assert node.labels == []
    assert node.properties == {}
    assert isinstance(node.created_at, datetime)
    assert isinstance(node.last_modified, datetime)

    # Create with custom args
    custom_time = datetime(2025, 1, 1)
    node = BaseNode(
        id="test-id",
        labels=["TestLabel"],
        properties={"test": "value"},
        created_at=custom_time,
        last_modified=custom_time,
    )
    assert node.id == "test-id"
    assert node.labels == ["TestLabel"]
    assert node.properties == {"test": "value"}
    assert node.created_at == custom_time
    assert node.last_modified == custom_time

    # Test to_dict method
    node_dict = node.to_dict()
    assert "id" not in node_dict
    assert node_dict["labels"] == ["TestLabel"]
    assert node_dict["properties"] == {"test": "value"}
    assert node_dict["test"] == "value"  # Properties should be expanded


def test_base_relationship() -> None:
    """Test BaseRelationship model."""
    # Create with required args
    rel = BaseRelationship(
        type="TEST",
        start_node_id="node1",
        end_node_id="node2",
    )
    assert rel.id is None
    assert rel.type == "TEST"
    assert rel.start_node_id == "node1"
    assert rel.end_node_id == "node2"
    assert rel.properties == {}
    assert isinstance(rel.created_at, datetime)

    # Create with custom args
    custom_time = datetime(2025, 1, 1)
    rel = BaseRelationship(
        id="test-id",
        type="TEST",
        start_node_id="node1",
        end_node_id="node2",
        properties={"test": "value"},
        created_at=custom_time,
    )
    assert rel.id == "test-id"
    assert rel.type == "TEST"
    assert rel.properties == {"test": "value"}
    assert rel.created_at == custom_time

    # Test to_dict method
    rel_dict = rel.to_dict()
    assert "id" not in rel_dict
    assert "start_node_id" not in rel_dict
    assert "end_node_id" not in rel_dict
    assert rel_dict["type"] == "TEST"
    assert rel_dict["test"] == "value"  # Properties should be expanded


def test_file_node() -> None:
    """Test FileNode model."""
    # Create with required args
    file_node = FileNode(
        path="/test/file.py",
        name="file.py",
    )
    assert file_node.path == "/test/file.py"
    assert file_node.name == "file.py"
    assert NodeType.FILE.value in file_node.labels

    # Create with all args
    file_node = FileNode(
        path="/test/file.py",
        name="file.py",
        extension=".py",
        size=1024,
        content="print('Hello world')",
        content_hash="abc123",
    )
    assert file_node.extension == ".py"
    assert file_node.size == 1024
    assert file_node.content == "print('Hello world')"
    assert file_node.content_hash == "abc123"

    # Test to_dict method
    file_dict = file_node.to_dict()
    assert file_dict["path"] == "/test/file.py"
    assert file_dict["name"] == "file.py"
    assert file_dict["extension"] == ".py"
    assert file_dict["content"] == "print('Hello world')"


def test_directory_node() -> None:
    """Test DirectoryNode model."""
    # Create with required args
    dir_node = DirectoryNode(
        path="/test",
        name="test",
    )
    assert dir_node.path == "/test"
    assert dir_node.name == "test"
    assert NodeType.DIRECTORY.value in dir_node.labels


def test_class_node() -> None:
    """Test ClassNode model."""
    # Create with required args
    class_node = ClassNode(
        name="TestClass",
    )
    assert class_node.name == "TestClass"
    assert class_node.methods == []
    assert class_node.base_classes == []
    assert NodeType.CLASS.value in class_node.labels

    # Create with all args
    class_node = ClassNode(
        name="TestClass",
        module="test_module",
        start_line=10,
        end_line=50,
        documentation="Test class documentation",
        code="class TestClass:\n    pass",
        methods=["method1", "method2"],
        base_classes=["BaseClass"],
    )
    assert class_node.module == "test_module"
    assert class_node.start_line == 10
    assert class_node.end_line == 50
    assert class_node.documentation == "Test class documentation"
    assert class_node.code == "class TestClass:\n    pass"
    assert class_node.methods == ["method1", "method2"]
    assert class_node.base_classes == ["BaseClass"]


def test_function_node() -> None:
    """Test FunctionNode model."""
    # Create with required args
    func_node = FunctionNode(
        name="test_function",
    )
    assert func_node.name == "test_function"
    assert func_node.parameters == []
    assert NodeType.FUNCTION.value in func_node.labels

    # Create with all args
    func_node = FunctionNode(
        name="test_function",
        module="test_module",
        start_line=10,
        end_line=20,
        documentation="Test function documentation",
        code="def test_function():\n    pass",
        signature="test_function()",
        parameters=[{"name": "arg1", "type": "str"}],
        return_type="None",
    )
    assert func_node.module == "test_module"
    assert func_node.signature == "test_function()"
    assert func_node.parameters == [{"name": "arg1", "type": "str"}]
    assert func_node.return_type == "None"


def test_method_node() -> None:
    """Test MethodNode model."""
    # Create with required args
    method_node = MethodNode(
        name="test_method",
        class_name="TestClass",
    )
    assert method_node.name == "test_method"
    assert method_node.class_name == "TestClass"
    assert NodeType.METHOD.value in method_node.labels
    assert NodeType.FUNCTION.value in method_node.labels


def test_module_node() -> None:
    """Test ModuleNode model."""
    # Create with required args
    module_node = ModuleNode(
        name="test_module",
    )
    assert module_node.name == "test_module"
    assert module_node.imports == []
    assert NodeType.MODULE.value in module_node.labels

    # Create with all args
    module_node = ModuleNode(
        name="test_module",
        imports=["os", "sys"],
    )
    assert module_node.imports == ["os", "sys"]


def test_summary_node() -> None:
    """Test SummaryNode model."""
    # Create with required args
    summary_node = SummaryNode(
        text="This is a summary",
    )
    assert summary_node.text == "This is a summary"
    assert summary_node.embedding is None
    assert summary_node.summary_type == "general"
    assert NodeType.SUMMARY.value in summary_node.labels

    # Create with all args
    summary_node = SummaryNode(
        text="This is a summary",
        embedding=[0.1, 0.2, 0.3],
        summary_type="class",
    )
    assert summary_node.embedding == [0.1, 0.2, 0.3]
    assert summary_node.summary_type == "class"


def test_documentation_node() -> None:
    """Test DocumentationNode model."""
    # Create with required args
    doc_node = DocumentationNode(
        content="This is documentation",
    )
    assert doc_node.content == "This is documentation"
    assert doc_node.doc_type == "inline"
    assert doc_node.embedding is None
    assert NodeType.DOCUMENTATION.value in doc_node.labels

    # Create with all args
    doc_node = DocumentationNode(
        content="This is documentation",
        doc_type="docstring",
        embedding=[0.1, 0.2, 0.3],
    )
    assert doc_node.doc_type == "docstring"
    assert doc_node.embedding == [0.1, 0.2, 0.3]


def test_contains_relationship() -> None:
    """Test ContainsRelationship model."""
    # Create with required args
    rel = ContainsRelationship(
        start_node_id="dir1",
        end_node_id="file1",
    )
    assert rel.type == RelationshipType.CONTAINS.value
    assert rel.start_node_id == "dir1"
    assert rel.end_node_id == "file1"


def test_imports_relationship() -> None:
    """Test ImportsRelationship model."""
    # Create with required args
    rel = ImportsRelationship(
        start_node_id="module1",
        end_node_id="module2",
    )
    assert rel.type == RelationshipType.IMPORTS.value


def test_calls_relationship() -> None:
    """Test CallsRelationship model."""
    # Create with required args
    rel = CallsRelationship(
        start_node_id="func1",
        end_node_id="func2",
    )
    assert rel.type == RelationshipType.CALLS.value
    assert rel.call_line is None

    # Create with all args
    rel = CallsRelationship(
        start_node_id="func1",
        end_node_id="func2",
        call_line=42,
    )
    assert rel.call_line == 42


def test_inherits_from_relationship() -> None:
    """Test InheritsFromRelationship model."""
    # Create with required args
    rel = InheritsFromRelationship(
        start_node_id="class1",
        end_node_id="class2",
    )
    assert rel.type == RelationshipType.INHERITS_FROM.value


def test_documented_by_relationship() -> None:
    """Test DocumentedByRelationship model."""
    # Create with required args
    rel = DocumentedByRelationship(
        start_node_id="class1",
        end_node_id="doc1",
    )
    assert rel.type == RelationshipType.DOCUMENTED_BY.value


def test_summarized_by_relationship() -> None:
    """Test SummarizedByRelationship model."""
    # Create with required args
    rel = SummarizedByRelationship(
        start_node_id="file1",
        end_node_id="summary1",
    )
    assert rel.type == RelationshipType.SUMMARIZED_BY.value
