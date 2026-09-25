from dataclasses import dataclass, asdict
from django.conf import settings


@dataclass(frozen=True)
class NodeIdentity:
    node_id: str
    project_slug: str
    tenant_slug: str
    deployment_id: str

    def as_dict(self):
        return asdict(self)


def get_node_identity() -> NodeIdentity:
    return NodeIdentity(
        node_id=getattr(settings, 'MEDIA_ENGINE_NODE_ID', 'local-node'),
        project_slug=getattr(settings, 'MEDIA_ENGINE_PROJECT_SLUG', 'local-project'),
        tenant_slug=getattr(settings, 'MEDIA_ENGINE_TENANT_SLUG', 'default'),
        deployment_id=getattr(settings, 'MEDIA_ENGINE_DEPLOYMENT_ID', 'standalone'),
    )


def scoped_owner_ref(owner_ref: str) -> str:
    identity = get_node_identity()
    clean = (owner_ref or '').strip()
    prefix = f'{identity.project_slug}:{identity.tenant_slug}'
    return f'{prefix}:{clean}' if clean else prefix
