package com.zeroone.star.othermana.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.query.j8.other.goodsbrand.GoodsBrandQuery;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandAddReqVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandNameVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandUpdateOprationRespVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandUpdateReqVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandVO;

import java.util.List;

/**
* @author 陈尚益
* @description 针对表【ba_goods_brand(品牌信息)】的数据库操作Service
* @createDate 2025-03-08 11:38:45
*/
public interface BaGoodsBrandService extends IService<GoodsBrandVO> {

    /** 名称列表（下拉框用） */
    List<GoodsBrandNameVO> queryGoodsBrandNameList();

    /** 条件分页查询 */
    PageDTO<GoodsBrandVO> queryGoodsBrandPage(GoodsBrandQuery query);

    /** 按条件查询全部（导出用，不分页） */
    List<GoodsBrandVO> queryGoodsBrandAll(GoodsBrandQuery query);

    boolean addGoodsBrand(GoodsBrandAddReqVO goodsBrandAddReqVO);

    GoodsBrandUpdateOprationRespVO oprationGetById(String id);

    /** 提交修改 */
    boolean updateGoodsBrand(GoodsBrandUpdateReqVO vo);

    boolean saveAll(List<GoodsBrandVO> list);
}
