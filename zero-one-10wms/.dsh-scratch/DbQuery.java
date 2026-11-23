import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class DbQuery {
    public static void main(String[] args) throws Exception {
        Class.forName("com.mysql.cj.jdbc.Driver");
        String url = "jdbc:mysql://192.168.89.128:3306/zo_wms?useUnicode=true&useSSL=false&characterEncoding=utf-8&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true";
        try (Connection c = DriverManager.getConnection(url, "root", "123456");
             Statement s = c.createStatement()) {
            try (ResultSet r = s.executeQuery("select username, password from t_s_base_user")) {
                while (r.next()) {
                    System.out.println("USER: " + r.getString(1) + " | " + r.getString(2));
                }
            }
            try (ResultSet r = s.executeQuery("select order_type_code, order_type_name from ba_order_type order by order_type_code")) {
                while (r.next()) {
                    System.out.println("TYPE: " + r.getString(1) + " | " + r.getString(2));
                }
            }
            try (ResultSet r = s.executeQuery("select order_type_code, count(*) from wm_im_notice_h group by order_type_code")) {
                while (r.next()) {
                    System.out.println("NOTICE_TYPE: " + r.getString(1) + " | " + r.getString(2));
                }
            }
        }
    }
}
