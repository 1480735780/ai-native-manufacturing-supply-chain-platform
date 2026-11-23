package com.zeroone.star.j5.basezl.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.zeroone.star.j5.basezl.entity.rfid.RfidBuseDO;
import com.zeroone.star.j5.basezl.entity.rfid.RfidBuseExcelDO;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDAddDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDDetailDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDListDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDModifyDTO;
import com.zeroone.star.project.query.j5.basezl.rfid.RFIDQuery;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface RFIDService extends IService<RfidBuseDO> {
    PageDTO<RFIDListDTO> queryRFIDAll(RFIDQuery rfidQuery);

    RFIDDetailDTO queryRFIDDetail(String rfid);

    String addRfid(RFIDAddDTO rfidAddDTO);

    String modifyRfid(RFIDModifyDTO rfidModifyDTO);

    /**
     * 批量删除 RFID
     *
     * @param rfidList 主键集合
     * @return 实际删除条数
     */
    int deleteRfid(List<Long> rfidList);

    /**
     * 从 Excel 导入 RFID 数据
     *
     * @param file Excel 文件
     * @return 导入结果统计
     */
    String importRfid(MultipartFile file);

    /**
     * 导出用：按查询条件获取数据；query 为空时导出全部
     *
     * @param query 查询条件
     * @return Excel 数据
     */
    List<RfidBuseExcelDO> selectAll(RFIDQuery query);

    /**
     * 导出用：按主键批量获取数据
     *
     * @param ids 主键集合
     * @return Excel 数据
     */
    List<RfidBuseExcelDO> selectByIds(List<Long> ids);
}
