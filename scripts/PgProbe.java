import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class PgProbe {
    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "jdbc:postgresql://localhost:5432/postgres";
        String user = args.length > 1 ? args[1] : "postgres";
        String password = System.getenv("PGPASSWORD");
        if (password == null || password.isBlank()) {
            throw new IllegalArgumentException("PGPASSWORD environment variable is required.");
        }
        try (Connection conn = DriverManager.getConnection(url, user, password);
             Statement st = conn.createStatement()) {
            try (ResultSet rs = st.executeQuery(
                    "select current_database(), current_user, version()")) {
                if (rs.next()) {
                    System.out.println("database=" + rs.getString(1));
                    System.out.println("user=" + rs.getString(2));
                    System.out.println("version=" + rs.getString(3));
                }
            }
            try (ResultSet rs = st.executeQuery(
                    "select table_schema, table_name from information_schema.tables " +
                    "where table_schema not in ('pg_catalog','information_schema') " +
                    "order by table_schema, table_name limit 20")) {
                int count = 0;
                while (rs.next()) {
                    count++;
                    System.out.println("table=" + rs.getString(1) + "." + rs.getString(2));
                }
                System.out.println("listed_tables=" + count);
            }
        }
    }
}
