package com.example.termuxshell

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Vytvoření WebView bez nutnosti definovat layout XML
        webView = WebView(this).apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                // Umožňuje otevřít appku bez složitých caching problémů
                cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE 
            }
            
            // Zajišťuje, že se odkazy a redirecty otevírají v appce, nikoliv v systémovém prohlížeči
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()

            // Zaregistrování rozhraní pro komunikaci mezi JS a Androidem
            addJavascriptInterface(AndroidBridge(this@MainActivity), "AndroidBridge")
        }

        setContentView(webView)

        // Načtení výchozího kontejneru z Termux backendu
        val targetUrl = "http://127.0.0.1:5000/app-container/default.html"
        webView.loadUrl(targetUrl)
    }

    // Ošetření tlačítka zpět, aby fungovalo v rámci historie WebView
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}

/**
 * Rozhraní pro bezpečné volání Android hardwaru z webových kontejnerů.
 */
class AndroidBridge(private val context: Context) {

    @JavascriptInterface
    fun vibrate(durationMs: Long) {
        // Moderní API pro vibrace (Android 12+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            val vibrator = vibratorManager.defaultVibrator
            vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            // Zpětná kompatibilita pro starší zařízení
            @Suppress("DEPRECATION")
            val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(durationMs)
            }
        }
    }
}
