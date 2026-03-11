# CDSS COPD: Android to Django Full Integration Guide

This guide gives you production-ready Java code to connect your completed Android frontend (Java+XML) to the Django REST Framework (DRF) backend running locally.

## 1. Prerequisites (AndroidManifest.xml)
Ensure your Android app allows internet access and cleartext traffic (necessary for talking to the emulator via `http://`).

Add this to `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.INTERNET" />

<application
    ...
    android:usesCleartextTraffic="true"
    ...>
```

---

## 2. Dependencies (build.gradle - Module: app)
Add the following Retrofit and Gson dependencies:
```gradle
dependencies {
    // Retrofit
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    // OkHttp (for logging and interceptors)
    implementation 'com.squareup.okhttp3:okhttp:4.9.3'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.9.3'
}
```

---

## 3. Token Management (SessionManager.java)
Handles saving and retrieving your JWT tokens using `SharedPreferences`.

```java
import android.content.Context;
import android.content.SharedPreferences;

public class SessionManager {
    private static final String PREF_NAME = "CDSS_Session";
    private static final String KEY_ACCESS_TOKEN = "access_token";
    private static final String KEY_REFRESH_TOKEN = "refresh_token";
    private static final String KEY_ROLE = "user_role";
    private SharedPreferences pref;
    private SharedPreferences.Editor editor;

    public SessionManager(Context context) {
        pref = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        editor = pref.edit();
    }

    public void saveTokens(String access, String refresh, String role) {
        editor.putString(KEY_ACCESS_TOKEN, access);
        editor.putString(KEY_REFRESH_TOKEN, refresh);
        editor.putString(KEY_ROLE, role);
        editor.apply();
    }

    public String getAccessToken() {
        return pref.getString(KEY_ACCESS_TOKEN, null);
    }
    
    public String getRole() {
        return pref.getString(KEY_ROLE, null);
    }

    public void logout() {
        editor.clear();
        editor.apply();
    }
}
```

---

## 4. Retrofit Setup & Interceptor (RetrofitClient.java)
Automatically attaches the JWT token to every request containing the `Authorization` header.

```java
import android.content.Context;
import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;
import java.io.IOException;

public class RetrofitClient {
    // For Android Emulator targeting localhost backend
    private static final String BASE_URL = "http://10.0.2.2:8000/"; 
    private static Retrofit retrofit = null;

    public static Retrofit getClient(Context context) {
        if (retrofit == null) {
            HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
            logging.setLevel(HttpLoggingInterceptor.Level.BODY);

            OkHttpClient client = new OkHttpClient.Builder()
                .addInterceptor(logging)
                .addInterceptor(new Interceptor() {
                    @Override
                    public Response intercept(Chain chain) throws IOException {
                        Request originalRequest = chain.request();
                        
                        // Skip token for auth endpoints (login/signup)
                        if (originalRequest.url().encodedPath().contains("/auth/")) {
                            return chain.proceed(originalRequest);
                        }

                        SessionManager session = new SessionManager(context);
                        String token = session.getAccessToken();

                        if (token != null) {
                            Request newRequest = originalRequest.newBuilder()
                                    .header("Authorization", "Bearer " + token)
                                    .build();
                            return chain.proceed(newRequest);
                        }
                        return chain.proceed(originalRequest);
                    }
                }).build();

            retrofit = new Retrofit.Builder()
                    .baseUrl(BASE_URL)
                    .addConverterFactory(GsonConverterFactory.create())
                    .client(client)
                    .build();
        }
        return retrofit;
    }
}
```

---

## 5. API Interface (ApiService.java)
Maps your Django `urls.py` endpoints to Java methods.

```java
import java.util.List;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface ApiService {
    // 1. Authentication
    @POST("api/auth/login/")
    Call<LoginResponse> login(@Body LoginRequest request);

    @POST("api/auth/signup/")
    Call<GenericResponse> signup(@Body SignupRequest request);

    // 2. Patient Management (Staff & Doctor)
    @GET("api/patients/")
    Call<List<PatientResponse>> getPatients();

    @POST("api/patients/")
    Call<PatientResponse> addPatient(@Body PatientRequest request);

    // 3. Clinical Data
    @POST("api/patients/{id}/abg/")
    Call<GenericResponse> addABGData(@Path("id") int patientId, @Body ABGRequest request);

    // 4. Alerts & Recommendations
    @GET("api/alerts/")
    Call<List<AlertResponse>> getAlerts();

    @GET("api/patients/{id}/recommendations/")
    Call<List<RecommendationResponse>> getPatientRecommendations(@Path("id") int patientId);

    @POST("api/recommendations/{id}/handle/")
    Call<GenericResponse> handleRecommendation(@Path("id") int recId, @Body HandleRecommendationRequest request);
}
```

---

## 6. Request & Response Models (POJOs)

**LoginRequest.java**
```java
public class LoginRequest {
    private String username;
    private String password;
    private String role; // "doctor", "staff", "admin"

    public LoginRequest(String username, String password, String role) {
        this.username = username;
        this.password = password;
        this.role = role;
    }
}
```

**LoginResponse.java**
```java
public class LoginResponse {
    private Tokens tokens;
    private UserData user;
    
    public Tokens getTokens() { return tokens; }
    public UserData getUser() { return user; }

    public class Tokens {
        private String access;
        private String refresh;
        public String getAccess() { return access; }
        public String getRefresh() { return refresh; }
    }
    
    public class UserData {
        private int id;
        private String username;
        private String role;
        public String getRole() { return role; }
    }
}
```

**ABGRequest.java**
```java
public class ABGRequest {
    private double ph;
    private double pao2;
    private double paco2;
    private double hco3;
    private double fio2;

    public ABGRequest(double ph, double pao2, double paco2, double hco3, double fio2) {
        this.ph = ph;
        this.pao2 = pao2;
        this.paco2 = paco2;
        this.hco3 = hco3;
        this.fio2 = fio2;
    }
}
```

**GenericResponse.java**
```java
public class GenericResponse {
    private String message;
    private String error;
    public String getMessage() { return message; }
    public String getError() { return error; }
}
```

*(Create similar simple classes for `PatientRequest`, `PatientResponse`, `AlertResponse`, `RecommendationResponse` mapping to the fields from the Django Serializers)*

---

## 7. Implementation Examples

### Example A: DoctorLoginActivity connecting to Backend
```java
// Inside DoctorLoginActivity.java
private void performLogin(String username, String password) {
    ApiService api = RetrofitClient.getClient(this).create(ApiService.class);
    LoginRequest request = new LoginRequest(username, password, "doctor");

    api.login(request).enqueue(new Callback<LoginResponse>() {
        @Override
        public void onResponse(Call<LoginResponse> call, Response<LoginResponse> response) {
            if (response.isSuccessful() && response.body() != null) {
                // Success (200 OK)
                String accessToken = response.body().getTokens().getAccess();
                String refreshToken = response.body().getTokens().getRefresh();
                
                SessionManager session = new SessionManager(DoctorLoginActivity.this);
                session.saveTokens(accessToken, refreshToken, "doctor");
                
                Toast.makeText(DoctorLoginActivity.this, "Login Successful", Toast.LENGTH_SHORT).show();
                startActivity(new Intent(DoctorLoginActivity.this, DoctordashboardActivity.class));
                finish();
            } else {
                // Handle 400 Bad Request, 401 Unauthorized, 403 Forbidden
                handleApiError(response.code());
            }
        }

        @Override
        public void onFailure(Call<LoginResponse> call, Throwable t) {
            // Handle 500 Server Error or No Internet Connection
            Toast.makeText(DoctorLoginActivity.this, "Network Error: " + t.getMessage(), Toast.LENGTH_LONG).show();
        }
    });
}

private void handleApiError(int code) {
    if (code == 401) {
        Toast.makeText(this, "Invalid credentials", Toast.LENGTH_LONG).show();
    } else if (code == 403) {
        Toast.makeText(this, "Account not approved by Admin yet", Toast.LENGTH_LONG).show();
    } else {
        Toast.makeText(this, "Error: " + code, Toast.LENGTH_SHORT).show();
    }
}
```

### Example B: ABGEntryActivity triggering AI Logic
```java
// Inside ABGEntryActivity.java
private void submitABGData(int patientId, double ph, double pao2, double paco2, double hco3, double fio2) {
    ApiService api = RetrofitClient.getClient(this).create(ApiService.class);
    ABGRequest request = new ABGRequest(ph, pao2, paco2, hco3, fio2);

    api.addABGData(patientId, request).enqueue(new Callback<GenericResponse>() {
        @Override
        public void onResponse(Call<GenericResponse> call, Response<GenericResponse> response) {
            if (response.isSuccessful()) {
                // If PaCO2 > 45, the backend automatically generated the NIV Recommendation and Notified doctors
                Toast.makeText(ABGEntryActivity.this, "ABG Saved Successfully", Toast.LENGTH_SHORT).show();
                finish();
            } else {
                Toast.makeText(ABGEntryActivity.this, "Failed to save: " + response.code(), Toast.LENGTH_SHORT).show();
            }
        }

        @Override
        public void onFailure(Call<GenericResponse> call, Throwable t) {
            Toast.makeText(ABGEntryActivity.this, "Network error", Toast.LENGTH_SHORT).show();
        }
    });
}
```

---

## 8. Testing your Implementation

1. **Start Django Server:** Make sure your Django backend is running in the `CDSS_COPD` folder (`python manage.py runserver 0.0.0.0:8000`).
2. **Postman Testing:** Before running in Android, open Postman.
   - Send `POST http://127.0.0.1:8000/api/auth/login/` with JSON Body: `{"username": "doc", "password": "123", "role": "doctor"}`.
   - Copy the `"access"` token.
   - Send `GET http://127.0.0.1:8000/api/patients/` with Header: `Authorization: Bearer <your_token>`. Ensure it returns `200 OK`.
3. **Android Emulator:** Run the app on the emulator. Since Retrofit uses `10.0.2.2:8000`, the emulator correctly routes traffic to your computer's `127.0.0.1:8000`. Watch your Android Studio `Logcat` because the `HttpLoggingInterceptor` will print the exact JSON Requests and Responses being sent from Android, helping you debug if the fields match perfectly.
