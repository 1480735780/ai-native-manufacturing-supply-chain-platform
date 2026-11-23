import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class BcryptCheck {
    public static void main(String[] args) {
        String hash = "$2a$10$XfGBDLEJ7H7nxvo.1VBcZu.tM65tgPCVPk8h.pNq38dutoNUffJOu";
        String[] candidates = {
                "admin", "admin123", "123456", "12345678", "123456789", "000000", "888888",
                "123123", "qwerty", "password", "01star", "zeroone", "ZeroOne", "123456a",
                "a123456", "admin@123", "1234567890", "111111", "666666"
        };
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        for (String candidate : candidates) {
            if (encoder.matches(candidate, hash)) {
                System.out.println("MATCH=" + candidate);
            }
        }
        System.out.println("DONE");
    }
}
