# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from patchlib import patch
R = "wms-cpp/wms-c7-reposity/"

patch(R+"controller/ba_act_type/BaActTypeController.cpp",
"""StringJsonVO::Wrapper BaActTypeController::execRemoveBaActType(const String& id) {
\tauto jvo = StringJsonVO::createShared();

\tif (id == "")
\t{
\t\tjvo->init(id, RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\tBaActTypeService service;
\tif (service.removeData(id)) {
\t\tjvo->success(id);
\t}
\telse
\t{
\t\tjvo->fail(id);
\t}
\treturn jvo;
}""",
"""StringJsonVO::Wrapper BaActTypeController::execRemoveBaActType(const String& id) {
\tauto jvo = StringJsonVO::createShared();

\tif (id == "")
\t{
\t\tjvo->init(id, RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\tBaActTypeService service;
\tif (service.removeData(id)) {
\t\tjvo->success(id);
\t}
\telse
\t{
\t\tjvo->fail(id);
\t}
\treturn jvo;
}

StringJsonVO::Wrapper BaActTypeController::execRemoveBaActTypeBatch(const String& ids) {
\tauto jvo = StringJsonVO::createShared();

\t// 参数校验
\tif (!ids || ids->empty())
\t{
\t\tjvo->init(ids, RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\tBaActTypeService service;
\t// 执行批量删除
\tif (service.removeDataBatch(ids->c_str())) {
\t\tjvo->success(ids);
\t}
\telse
\t{
\t\tjvo->fail(ids);
\t}
\treturn jvo;
}""")
