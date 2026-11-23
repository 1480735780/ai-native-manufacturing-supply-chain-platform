package com.zeroone.star.j5.basezl.entity.rfid;

import com.alibaba.excel.annotation.ExcelIgnore;
import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.format.DateTimeFormat;
import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Date;

/**
 * RFID 导入/导出 Excel 模型。
 * 列顺序与导出模板保持一致，导入时按表头名称匹配。
 */
@Data
public class RfidBuseExcelDO {
    //主键（导入时不使用，数据库自增）
    @ExcelIgnore
    @TableId(value = "id", type = IdType.ASSIGN_ID)
    private String id;

    /**创建人登录名称*/
    @ExcelProperty(value = "创建人", index = 0)
    private String createName;

    /**创建日期*/
    @ExcelProperty(value = "创建日期", index = 1)
    @DateTimeFormat("yyyy-MM-dd HH:mm:ss")
    private Date createDate;

    //更新日期
    @ExcelIgnore
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateDate;

    /**类型*/
    @ExcelProperty(value = "类型", index = 2)
    private String rfidType;

    /**业务编号*/
    @ExcelProperty(value = "业务编号", index = 3)
    private String rfidBuseno;

    /**业务内容*/
    @ExcelProperty(value = "业务内容", index = 4)
    private String rfidBusecont;

    /**RFID1*/
    @ExcelProperty(value = "RFID1", index = 5)
    private String rfidId1;

    /**RFID2*/
    @ExcelProperty(value = "RFID2", index = 6)
    private String rfidId2;

    /**RFID3*/
    @ExcelProperty(value = "RFID3", index = 7)
    private String rfidId3;
}
