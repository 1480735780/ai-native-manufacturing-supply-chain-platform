# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from patchlib import patch
R = "wms-cpp/wms-c7-reposity/"
patch(R+"dao/ordertypes/OrderTypesDAO.cpp",
"""#include <sstream>""",
"""#include <sstream>
#include <vector>""")
patch(R+"dao/ba_act_type/BaActTypeDAO.cpp",
"""#include <sstream>""",
"""#include <sstream>
#include <vector>""")
