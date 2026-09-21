from typing import Annotated

from fastapi import Depends

from app.core.security.rbac import require_roles
from app.enums.user import RoleEnum
from app.schemas.user import UserOut
from app.services.auth.auth import AuthService, get_auth_service
from app.services.auth.dependencies import get_current_user
from app.services.integration import IntegrationService, get_integration_service
from app.services.return_order import ReturnOrderService, get_return_order_service
from app.services.sku import SkuService, get_sku_service
from app.services.sku_import import SkuImportService, get_sku_import_service
from app.services.user import UserService, get_user_service
from app.services.wms_order import WmsOrderService, get_wms_order_service

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
SkuServiceDep = Annotated[SkuService, Depends(get_sku_service)]
SkuImportServiceDep = Annotated[SkuImportService, Depends(get_sku_import_service)]
ReturnOrderServiceDep = Annotated[ReturnOrderService, Depends(get_return_order_service)]
WmsOrderServiceDep = Annotated[WmsOrderService, Depends(get_wms_order_service)]
IntegrationServiceDep = Annotated[IntegrationService, Depends(get_integration_service)]

CurrentUserDep = Annotated[UserOut, Depends(get_current_user)]
AdminUserDep = Annotated[UserOut, Depends(require_roles(RoleEnum.ADMIN))]
