"""
Tests for the Frontend ISR Profile (Phase 2 of FEE runtime).

Validates that frontend entities extend the ISR model correctly,
the validator enforces constitutional rules, and the transformer
maintains ISR integrity.
"""

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System, SystemMetadata
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.entity import Entity, Relationship
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.isr_graph import ISRGraph

from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, DesignSystem, Component, ComponentNode,
    Layout, Page, Interaction, TokenDefinition, GridSystem,
    GenomeMapping, ChromosomeFamily, AccessibilityContract,
    PropertyDefinition, EventDefinition, FitnessTarget,
)
from constitutional_architecture.isr.profiles.frontend_validator import (
    FrontendProfileValidator, ProfileValidationResult,
)
from constitutional_architecture.isr.profiles.frontend_transformer import FrontendTransformer


# ==============================================================================
# Token definition tests
# ==============================================================================

class TestTokenDefinition:
    def test_creation(self):
        t = TokenDefinition(
            id="color-danger",
            semantic_role="Danger / Destructive",
            category="color",
            base_value="#DC2626",
            description="Used for destructive actions and error states",
        )
        assert t.id == "color-danger"
        assert t.semantic_role == "Danger / Destructive"
        assert t.category == "color"
        assert t.base_value == "#DC2626"

    def test_with_accessibility_constraints(self):
        t = TokenDefinition(
            id="color-primary",
            semantic_role="Primary Brand Color",
            category="color",
            base_value="#2563EB",
            accessibility_constraints={"minContrastRatio": 4.5, "wcagLevel": "AA"},
        )
        assert t.accessibility_constraints["minContrastRatio"] == 4.5


# ==============================================================================
# DesignSystem tests
# ==============================================================================

class TestDesignSystem:
    def test_empty_system(self):
        ds = DesignSystem(id="ds-1", name="Test Design System")
        assert ds.id == "ds-1"
        assert ds.name == "Test Design System"
        assert ds.tokens == {}

    def test_with_color_tokens(self):
        ds = DesignSystem(
            id="ds-2", name="E-Commerce",
            tokens={
                "color": {
                    "primary": TokenDefinition("primary", "Primary", "color", "#2563EB"),
                    "danger": TokenDefinition("danger", "Danger", "color", "#DC2626"),
                },
                "spacing": {
                    "md": TokenDefinition("md", "Medium", "spacing", "16px"),
                },
            },
        )
        assert len(ds.tokens["color"]) == 2
        assert ds.tokens["spacing"]["md"].base_value == "16px"

    def test_with_genome_mapping(self):
        genome = GenomeMapping(ChromosomeFamily.PRESENTATION, "gene-1", 0.15)
        ds = DesignSystem(id="ds-3", name="Genome Linked", genome=genome)
        assert ds.genome.chromosome_family == ChromosomeFamily.PRESENTATION
        assert ds.genome.mutation_rate == 0.15


# ==============================================================================
# Component tests
# ==============================================================================

class TestComponent:
    def test_minimal_component(self):
        c = Component(
            id="btn-1", name="PrimaryButton",
            purpose="Primary call-to-action button",
        )
        assert c.id == "btn-1"
        assert c.name == "PrimaryButton"
        assert c.purpose == "Primary call-to-action button"
        assert "default" in c.states

    def test_full_component(self):
        c = Component(
            id="card-1", name="ProductCard",
            purpose="Displays a product with image, title, price, and CTA",
            inputs=(
                PropertyDefinition("title", "string", True),
                PropertyDefinition("price", "number", True),
                PropertyDefinition("imageUrl", "string"),
            ),
            outputs=(
                EventDefinition("onAddToCart", "ProductSelected"),
            ),
            states=("default", "hover", "loading", "error"),
            variants=("compact", "detailed"),
            allowed_children=("Badge", "Button"),
            allowed_parents=("CardGroup", "Grid"),
            token_dependencies=("color-primary", "space-md"),
            accessibility_contract=AccessibilityContract(
                aria_role="article",
                keyboard_navigation=("Enter", "Space"),
                focus_management="sequential",
            ),
            genome=GenomeMapping(ChromosomeFamily.STRUCTURE, "gene-card-1"),
        )
        assert len(c.inputs) == 3
        assert len(c.outputs) == 1
        assert "loading" in c.states
        assert c.accessibility_contract.aria_role == "article"


# ==============================================================================
# ComponentNode tests
# ==============================================================================

class TestComponentNode:
    def test_leaf_node(self):
        node = ComponentNode(component_ref="PrimaryButton", props={"label": "Submit"})
        assert node.component_ref == "PrimaryButton"
        assert node.props["label"] == "Submit"
        assert node.children == ()

    def test_nested_tree(self):
        tree = ComponentNode(
            component_ref="ProductPage",
            children=(
                ComponentNode("Header", {"title": "Shop"}),
                ComponentNode("ProductGrid", {},
                    children=(
                        ComponentNode("ProductCard", {"id": "p1"}),
                        ComponentNode("ProductCard", {"id": "p2"}),
                    ),
                ),
                ComponentNode("Footer"),
            ),
        )
        assert len(tree.children) == 3
        assert tree.children[1].children[0].component_ref == "ProductCard"


# ==============================================================================
# Layout tests
# ==============================================================================

class TestLayout:
    def test_basic_layout(self):
        layout = Layout(
            id="main-layout", name="Main Application Shell",
            grid_system=GridSystem(columns=12, gutter_token_ref="space-md"),
            responsive_breakpoints=("sm", "md", "lg"),
            regions=(
                {"name": "header", "role": "header"},
                {"name": "sidebar", "role": "sidebar"},
                {"name": "main", "role": "main"},
            ),
        )
        assert layout.grid_system.columns == 12
        assert len(layout.regions) == 3


# ==============================================================================
# Page tests
# ==============================================================================

class TestPage:
    def test_page_with_data_refs(self):
        page = Page(
            id="products-page", name="Products Listing",
            route_pattern="/products",
            layout_ref="main-layout",
            component_tree=ComponentNode("ProductsPage", {}, (
                ComponentNode("SearchBar"),
                ComponentNode("ProductGrid"),
            )),
            data_requirements=("api:list-products", "api:get-categories"),
            genome=GenomeMapping(ChromosomeFamily.STRUCTURE, "gene-prod-page"),
        )
        assert page.route_pattern == "/products"
        assert len(page.data_requirements) == 2
        assert page.genome.chromosome_family == ChromosomeFamily.STRUCTURE

    def test_page_with_view_states(self):
        page = Page(
            id="detail-page", name="Product Detail",
            route_pattern="/products/:id",
            layout_ref="detail-layout",
            component_tree=ComponentNode("DetailPage"),
            data_requirements=("api:get-product",),
            view_states={
                "loading": ComponentNode("Skeleton"),
                "empty": ComponentNode("EmptyState", {"message": "Product not found"}),
                "error": ComponentNode("ErrorState", {"retry": True}),
            },
        )
        assert "loading" in page.view_states
        assert "empty" in page.view_states


# ==============================================================================
# FrontendISRProfile tests
# ==============================================================================

class TestFrontendISRProfile:
    def test_minimal_profile(self):
        ds = DesignSystem(id="ds-min", name="Minimal")
        profile = FrontendISRProfile(design_system=ds)
        assert profile.design_system.name == "Minimal"
        assert profile.components == ()
        assert profile.pages == ()

    def test_full_profile(self):
        ds = DesignSystem(id="ds-full", name="E-Commerce Pro",
            tokens={
                "color": {"primary": TokenDefinition("primary", "Primary", "color", "#2563EB")},
                "spacing": {"md": TokenDefinition("md", "Medium", "spacing", "16px")},
            },
        )
        btn = Component(id="btn", name="Button", purpose="Action trigger")
        card = Component(id="card", name="Card", purpose="Content container")
        layout = Layout(id="main", name="Main Shell")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="main",
                    component_tree=ComponentNode("HomePage"))
        profile = FrontendISRProfile(
            design_system=ds,
            components=(btn, card),
            layouts=(layout,),
            pages=(page,),
        )
        assert len(profile.components) == 2
        assert len(profile.pages) == 1
        assert len(profile.layouts) == 1


# ==============================================================================
# FrontendProfileValidator tests
# ==============================================================================

class TestFrontendProfileValidator:
    def test_valid_profile_passes(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"primary": TokenDefinition("primary", "Primary", "color", "#000")}},
        )
        comp = Component(id="btn", name="Btn", purpose="Click me",
                         accessibility_contract=AccessibilityContract(aria_role="button"))
        layout = Layout(id="main", name="Main")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="main",
                    component_tree=ComponentNode("Root"))
        profile = FrontendISRProfile(ds, components=(comp,), layouts=(layout,), pages=(page,))
        validator = FrontendProfileValidator()
        result = validator.validate(profile)
        assert result.passed is True

    def test_missing_purpose_fails(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        comp = Component(id="bad", name="Bad", purpose="")
        layout = Layout(id="main", name="Main")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="main",
                    component_tree=ComponentNode("Root"))
        profile = FrontendISRProfile(ds, components=(comp,), layouts=(layout,), pages=(page,))
        result = FrontendProfileValidator().validate(profile)
        assert result.passed is False
        assert any("purpose" in e for e in result.errors)

    def test_missing_default_state_fails(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        comp = Component(id="bad", name="Bad", purpose="Test", states=("hover",))
        layout = Layout(id="main", name="Main")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="main",
                    component_tree=ComponentNode("Root"))
        profile = FrontendISRProfile(ds, components=(comp,), layouts=(layout,), pages=(page,))
        result = FrontendProfileValidator().validate(profile)
        assert result.passed is False
        assert any("default" in e for e in result.errors)

    def test_unknown_layout_ref_fails(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        comp = Component(id="btn", name="Btn", purpose="Test")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="nonexistent",
                    component_tree=ComponentNode("Root"))
        profile = FrontendISRProfile(ds, components=(comp,), pages=(page,))
        result = FrontendProfileValidator().validate(profile)
        assert result.passed is False
        assert any("unknown layout" in e for e in result.errors)

    def test_missing_token_category_warns(self):
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds)
        result = FrontendProfileValidator().validate(profile)
        assert result.passed is False
        assert any("token category" in e for e in result.errors)

    def test_missing_aria_role_warns(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        comp = Component(id="btn", name="Btn", purpose="Test",
                         accessibility_contract=AccessibilityContract())
        layout = Layout(id="main", name="Main")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="main",
                    component_tree=ComponentNode("Root"))
        profile = FrontendISRProfile(ds, components=(comp,), layouts=(layout,), pages=(page,))
        result = FrontendProfileValidator().validate(profile)
        assert result.passed is True  # aria role is a warning, not error
        assert any("ARIA role" in w for w in result.warnings)


# ==============================================================================
# FrontendTransformer tests
# ==============================================================================

class TestFrontendTransformer:
    def test_embed_and_extract(self):
        isr = ISR(
            system=System(
                id="test-1", name="TestSystem",
                modules=(
                    Module(id="mod-1", name="Core"),
                ),
                metadata=SystemMetadata(version="1.0"),
            ),
        )
        ds = DesignSystem(id="ds-1", name="Test DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        profile = FrontendISRProfile(ds)

        embedded = FrontendTransformer.embed_profile(isr, profile)
        assert embedded is not None
        assert embedded.version == isr.version + 1

    def test_data_ref_integrity(self):
        isr = ISR(
            system=System(
                id="test-2", name="Shop",
                modules=(
                    Module(
                        id="mod-catalog", name="Catalog",
                        entities=(
                            Entity(id="ent-product", name="Product", fields=(
                                Field("id", FieldType.UUID, is_primary_key=True),
                            )),
                        ),
                        services=(
                            Service(id="svc-products", name="ProductService",
                                operations=(Operation("list", "listProducts", OperationType.QUERY),),
                            ),
                        ),
                    ),
                ),
            ),
        )
        graph = ISRGraph(isr.system)
        refs = FrontendTransformer.build_data_requirement_refs(graph)
        assert "Catalog" in refs
        assert len(refs["Catalog"]) >= 2

        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        good_page = Page(id="p1", name="Products", route_pattern="/products",
                         layout_ref="main", component_tree=ComponentNode("Page"),
                         data_requirements=("entity:Catalog:Product",))
        bad_page = Page(id="p2", name="Broken", route_pattern="/broken",
                        layout_ref="main", component_tree=ComponentNode("Page"),
                        data_requirements=("nonexistent:ref",))
        profile = FrontendISRProfile(ds, pages=(good_page, bad_page))

        broken = FrontendTransformer.check_page_data_integrity(profile, graph)
        assert len(broken) == 1
        assert "nonexistent" in broken[0]
