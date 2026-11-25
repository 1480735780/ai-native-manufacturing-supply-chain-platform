package com.zeroone.star.project.j3.daycheck;

import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.NoUpGoodsDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.http.ResponseEntity;

import java.util.List;

public interface NoUpApis {
    /**
     * 查询收货未上架--每日检查
     * 根据条件分页查询
     * @param condition
     * @return
     */
    public JsonVO<List<NoUpGoodsDTO>> getNoUpGoods(NoUpGoodsQuery condition);

    /**
     * 巡检专用分页查询：返回 rows/total/pages，旧端点契约不变。
     */
    public JsonVO<PageDTO<NoUpGoodsDTO>> getNoUpGoodsPaged(NoUpGoodsQuery condition);

    /**
     * 根据条件生成excel文档
     * @param
     * @return
     */
    public ResponseEntity<byte[]> downLoadNoUp();
}
