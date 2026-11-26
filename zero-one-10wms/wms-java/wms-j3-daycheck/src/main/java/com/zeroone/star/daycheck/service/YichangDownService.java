package com.zeroone.star.daycheck.service;


import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.YichangDownDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;

import java.util.List;

public interface YichangDownService {

    List<YichangDownDTO> getYichangDownPage(YichangDownQuery condition);

    /** 巡检专用分页端点：返回 rows/total/pages 与稳定 rowId，旧端点契约不变。 */
    PageDTO<YichangDownDTO> getYichangDownPageDTO(YichangDownQuery condition);

    List<YichangDown> getYichangDownDate();
}
