(function () {
    "use strict";

    var FIREBASE_CONFIG = {
        apiKey: "AIzaSyDxgpXtgQQKtFPKYppu7HByBVxyib6vS1k",
        authDomain: "marifetlieller-42.firebaseapp.com",
        projectId: "marifetlieller-42",
        storageBucket: "marifetlieller-42.firebasestorage.app",
        messagingSenderId: "632366040975",
        appId: "1:632366040975:web:15e8a77207e3c3ac326dfa"
    };
    var APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxUwJTckSQ52vHT9GAKOFTOvyryxRyoeR32q7yIZt9MhPYBwO1VikmIosC-VzyqUd33/exec";
    var ARAMA_INDEX_URL = "arama_index.json?v=20261116_1";

    var aramaIndexCache = null;
    var aramaIndexPromise = null;

    function escapeHtml(str) {
        return String(str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function ensureFirebase() {
        if (typeof firebase !== "undefined" && firebase.apps && !firebase.apps.length) {
            firebase.initializeApp(FIREBASE_CONFIG);
        }
        return typeof firebase !== "undefined" && typeof firebase.auth === "function";
    }

    function getAramaIndex() {
        if (Array.isArray(window.videoVeritabani) && window.videoVeritabani.length > 0) {
            aramaIndexCache = window.videoVeritabani;
            return Promise.resolve(aramaIndexCache);
        }
        if (aramaIndexCache) {
            return Promise.resolve(aramaIndexCache);
        }
        if (aramaIndexPromise) {
            return aramaIndexPromise;
        }
        aramaIndexPromise = fetch(ARAMA_INDEX_URL)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                aramaIndexCache = Array.isArray(data) ? data : [];
                window.videoVeritabani = aramaIndexCache;
                return aramaIndexCache;
            })
            .catch(function () {
                aramaIndexPromise = null;
                return [];
            });
        return aramaIndexPromise;
    }

    window.marifetliAramaIndexGetir = getAramaIndex;

    if (typeof window.cikisYap !== "function") {
        window.cikisYap = function () {
            if (ensureFirebase()) {
                firebase.auth().signOut().then(function () {
                    window.location.reload();
                });
            }
        };
    }

    if (typeof window.menuGoster !== "function") {
        window.menuGoster = function () {
            var nav = document.getElementById("navLinks");
            if (nav) nav.classList.toggle("aktif");
        };
    }

    if (typeof window.mobilDropdownAc !== "function") {
        window.mobilDropdownAc = function (element) {
            if (window.innerWidth <= 860 && element && element.parentElement) {
                element.parentElement.classList.toggle("aktif");
            }
        };
    }

    function renderAramaSonuclari(aranan, veri, sonucKutusu) {
        var filtrelenmis = veri.filter(function (video) {
            var basliktaVar = video.baslik && video.baslik.toLowerCase().includes(aranan);
            var ozetteVar = video.ozet && video.ozet.toLowerCase().includes(aranan);
            var aciklamadaVar = video.aciklama && video.aciklama.toLowerCase().includes(aranan);
            var makaledeVar = video.makale && video.makale.toLowerCase().includes(aranan);
            var katVar = video.baskin_kategori && video.baskin_kategori.toLowerCase().includes(aranan);
            return basliktaVar || ozetteVar || aciklamadaVar || makaledeVar || katVar;
        });

        if (filtrelenmis.length > 0) {
            sonucKutusu.innerHTML = filtrelenmis.slice(0, 10).map(function (video) {
                var baslikSafe = escapeHtml(video.baslik);
                var fav = escapeHtml(video.favori_sayisi || "980");
                return '<a href="' + escapeHtml(video.link) + '" class="arama-sonuc-oge" style="display:flex; align-items:center; gap:12px; padding:10px; border-bottom:1px solid #eee; text-decoration:none; color:#333;">' +
                    '<img src="' + escapeHtml(video.resim) + '" alt="' + baslikSafe + '" loading="lazy" style="width:60px; height:40px; border-radius:6px; object-fit:cover;">' +
                    '<div style="display: flex; flex-direction: column; gap: 4px;">' +
                        '<span style="font-size:13px; font-weight: 500; line-height: 1.2;">' + baslikSafe + '</span>' +
                        '<span style="font-size:11px; color:#d6336c; font-weight: 600;">❤️ ' + fav + ' favori</span>' +
                    '</div>' +
                '</a>';
            }).join("");
            sonucKutusu.style.display = "block";
        } else {
            sonucKutusu.innerHTML = '<div style="padding:15px; font-size:13px; text-align:center;">Sonuç bulunamadı.</div>';
            sonucKutusu.style.display = "block";
        }
    }

    window.aramaYap = function () {
        var inputEl = document.getElementById("aramaInput");
        var sonucKutusu = document.getElementById("aramaSonuclari");
        if (!inputEl || !sonucKutusu) return;

        var aranan = inputEl.value.toLowerCase().trim();
        if (aranan.length < 2) {
            sonucKutusu.style.display = "none";
            return;
        }

        if (aramaIndexCache) {
            renderAramaSonuclari(aranan, aramaIndexCache, sonucKutusu);
            return;
        }

        sonucKutusu.innerHTML = '<div style="padding:12px; font-size:13px; text-align:center; color:#888;">Aranıyor...</div>';
        sonucKutusu.style.display = "block";
        getAramaIndex().then(function (veri) {
            var guncelAranan = inputEl.value.toLowerCase().trim();
            if (guncelAranan.length < 2) {
                sonucKutusu.style.display = "none";
                return;
            }
            renderAramaSonuclari(guncelAranan, veri, sonucKutusu);
        });
    };

    window.whatsappPaylas = function (baslik) {
        var url = window.location.href;
        var mesaj = baslik + " - Marifetli Eller'de harika bir model gördüm! Mutlaka incele: " + url;
        window.open("https://api.whatsapp.com/send?text=" + encodeURIComponent(mesaj), "_blank");
    };

    window.facebookPaylas = function () {
        var url = window.location.href;
        window.open("https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url), "_blank");
    };

    window.pinterestPaylas = function (baslik) {
        var url = window.location.href;
        window.open("https://pinterest.com/pin/create/button/?url=" + encodeURIComponent(url) + "&description=" + encodeURIComponent(baslik), "_blank");
    };

    window.instagramIcinKopyala = function () {
        var sayfaLinki = window.location.href;
        navigator.clipboard.writeText(sayfaLinki).then(function () {
            alert("✨ Sayfa linki kopyalandı!\n\nŞimdi Instagram'ı açıp bu linki 'Hikaye'nizde (Çıkartmalar > Bağlantı) veya profilinizde kolayca paylaşabilirsiniz.");
        }).catch(function () {
            alert("Link kopyalanamadı. Tarayıcınızın adres çubuğundan linki manuel olarak kopyalayabilirsiniz.");
        });
    };

    window.favoriIslemiYap = function (btn, modelId, baslik, link, resim) {
        var currentUser = ensureFirebase() ? firebase.auth().currentUser : null;
        var userEmail = (currentUser && currentUser.email) || localStorage.getItem("kullaniciEmail");
        if (!userEmail) {
            userEmail = localStorage.getItem("anonim_id");
            if (!userEmail) {
                userEmail = "anonim_" + Math.random().toString(36).substr(2, 9);
                localStorage.setItem("anonim_id", userEmail);
            }
        }

        btn.innerHTML = "⏳ İşleniyor...";
        btn.disabled = true;

        var islenmisResim = resim || "";
        if (islenmisResim.includes("drive.google.com/file/d/")) {
            var id = islenmisResim.split("file/d/")[1].split("/")[0];
            islenmisResim = "https://lh3.googleusercontent.com/d/" + id;
        } else if (islenmisResim.includes("youtube.com") || islenmisResim.includes("youtu.be")) {
            var videoId = islenmisResim.includes("v=")
                ? islenmisResim.split("v=")[1].substring(0, 11)
                : islenmisResim.split("youtu.be/")[1].substring(0, 11);
            islenmisResim = "https://img.youtube.com/vi/" + videoId + "/hqdefault.jpg";
        }

        var formData = new URLSearchParams();
        formData.append("islem", "favori_islem");
        formData.append("email", userEmail);
        formData.append("model_id", modelId);
        formData.append("baslik", baslik);
        formData.append("link", link);
        formData.append("resim", islenmisResim);

        fetch(APPS_SCRIPT_URL, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData.toString(),
            redirect: "follow"
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                btn.disabled = false;
                var sayac = document.getElementById("guncelFavoriSayisi");
                if (data.durum === "eklendi") {
                    btn.classList.add("aktif");
                    btn.innerHTML = "❤️ Favorilerde";
                    if (sayac) sayac.innerText = parseInt(sayac.innerText, 10) + 1;
                } else if (data.durum === "cikarildi") {
                    btn.classList.remove("aktif");
                    btn.innerHTML = "🤍 Favorilere Ekle";
                    if (sayac) sayac.innerText = parseInt(sayac.innerText, 10) - 1;
                } else {
                    alert(data.mesaj);
                    btn.innerHTML = "🤍 Favorilere Ekle";
                }
            })
            .catch(function (err) {
                console.error(err);
                alert("Arka planda kaydedildi.");
                btn.disabled = false;
                btn.innerHTML = "🤍 Favorilere Ekle";
            });
    };

    function favoriDurumunuYukle(user) {
        var favoriBtn = document.querySelector(".favori-btn");
        if (!favoriBtn) return;
        var sorguEmail = user ? user.email : (localStorage.getItem("anonim_id") || "");
        var modelId = favoriBtn.id.replace("btnFavori_", "");
        if (!modelId || !sorguEmail) return;

        fetch(APPS_SCRIPT_URL + "?islem=favori_durum&email=" + encodeURIComponent(sorguEmail) + "&model_id=" + encodeURIComponent(modelId))
            .then(function (res) { return res.json(); })
            .then(function (data) {
                favoriBtn.disabled = false;
                if (data.durum === "ekli") {
                    favoriBtn.classList.add("aktif");
                    favoriBtn.innerHTML = "❤️ Favorilerde";
                } else {
                    favoriBtn.classList.remove("aktif");
                    favoriBtn.innerHTML = "🤍 Favorilere Ekle";
                }
                if (data.toplam !== undefined) {
                    var sayac = document.getElementById("guncelFavoriSayisi");
                    if (sayac) sayac.innerText = data.toplam;
                }
            })
            .catch(function (err) {
                console.log("Canlı veriler okunamadı: ", err);
            });
    }

    function haftaninModelleriniGuncelle() {
        var grid = document.getElementById("haftaninPopulerGrid");
        if (!grid) return;

        var suAn = new Date();
        var d = new Date(Date.UTC(suAn.getFullYear(), suAn.getMonth(), suAn.getDate()));
        var gunNo = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - gunNo);
        var yilBasi = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        var haftaNo = Math.ceil((((d - yilBasi) / 86400000) + 1) / 7);

        getAramaIndex()
            .then(function (veriler) {
                if (!Array.isArray(veriler) || veriler.length < 10) return;
                var adaylar = veriler.slice(0, 60);
                var baslangic = (haftaNo * 5) % Math.max(1, adaylar.length - 5);
                var secilenler = adaylar.slice(baslangic, baslangic + 5);

                var html = "";
                for (var i = 0; i < secilenler.length; i++) {
                    var vid = secilenler[i];
                    var baslikSafe = escapeHtml(vid.baslik);
                    var fav = escapeHtml(vid.favori_sayisi || (571 + ((haftaNo * 37) % 5000)));
                    html += '<a href="' + escapeHtml(vid.link) + '" class="video-kart" style="border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.05); transition: transform 0.2s;">' +
                        '<div class="kart-resim" style="border-radius: 8px;">' +
                            '<img src="' + escapeHtml(vid.resim) + '" alt="' + baslikSafe + '" loading="lazy" decoding="async">' +
                        '</div>' +
                        '<div style="padding: 10px 5px;">' +
                            '<h4 style="margin:0; font-size: 13px; color: var(--metin-koyu); line-height: 1.3;">' + baslikSafe + '</h4>' +
                            '<div style="margin-top: 5px; font-size: 11px; color: #d6336c; font-weight: 600;">' +
                                '❤️ <span class="fav-sayac">' + fav + '</span> favori' +
                            '</div>' +
                        '</div>' +
                    '</a>';
                }
                grid.innerHTML = html;
            })
            .catch(function () {});
    }

    function initSite() {
        var aramaInput = document.getElementById("aramaInput");
        if (aramaInput) {
            aramaInput.addEventListener("focus", getAramaIndex, { once: true });
            aramaInput.addEventListener("mouseenter", getAramaIndex, { once: true });
        }

        if (ensureFirebase()) {
            firebase.auth().onAuthStateChanged(function (user) {
                var kullaniciAlan = document.getElementById("kullaniciAlan");
                if (user) {
                    var displayName = user.displayName || (user.email ? user.email.split("@")[0] : "Üye");
                    localStorage.setItem("kullaniciEmail", user.email || "");
                    localStorage.setItem("kullaniciAdi", displayName);
                    if (kullaniciAlan) {
                        var safeName = escapeHtml(displayName);
                        kullaniciAlan.innerHTML =
                            '<div style="display: flex; align-items: center; gap: 8px; background: var(--hover-renk); padding: 4px 6px 4px 15px; border-radius: 25px; border: 1px solid var(--kenarlik);">' +
                                '<span style="font-size: 13px; font-weight: 600; color: var(--ana-renk);">' + safeName + '</span>' +
                                '<a href="profil.html" style="background: var(--ana-renk); color: white; border: none; padding: 5px 12px; border-radius: 20px; text-decoration: none; font-size: 12px; font-weight: 500; transition: 0.2s;">👤 Profilim</a>' +
                                '<button onclick="cikisYap()" style="background: white; border: 1px solid var(--kenarlik); padding: 5px 12px; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: 500; color: var(--metin-koyu); transition: 0.2s;">Çıkış Yap</button>' +
                            '</div>';
                    }
                } else {
                    localStorage.removeItem("kullaniciEmail");
                    localStorage.removeItem("kullaniciAdi");
                    if (kullaniciAlan) {
                        kullaniciAlan.innerHTML = '<a href="giris.html" style="background: var(--ana-renk); color: white; padding: 8px 18px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: 500; white-space: nowrap;">Giriş Yap</a>';
                    }
                }
                favoriDurumunuYukle(user);
            });
        } else {
            favoriDurumunuYukle(null);
        }

        var sayfaSayacEl = document.getElementById("sayfa-sayac");
        if (sayfaSayacEl) {
            var sayfaID = sayfaSayacEl.getAttribute("data-sayfa-id");
            if (!sayfaID) {
                sayfaID = window.location.pathname.split("/").pop().replace(/[^a-zA-Z0-9]/g, "");
                if (!sayfaID || sayfaID === "indexhtml") sayfaID = "anasayfa";
            }
            fetch(APPS_SCRIPT_URL + "?islem=sayac&sayfa_id=" + encodeURIComponent(sayfaID))
                .then(function (response) { return response.text(); })
                .then(function (data) {
                    if (data && !isNaN(data) && data !== "0") {
                        sayfaSayacEl.innerText = data;
                    } else {
                        sayfaSayacEl.innerText = "1";
                    }
                })
                .catch(function (error) {
                    console.error("Sayaç hatası:", error);
                    sayfaSayacEl.innerText = "-";
                });
        }

        haftaninModelleriniGuncelle();
    }

    ensureFirebase();

    document.addEventListener("click", function (e) {
        if (!e.target.closest(".arama-alani")) {
            var sonuc = document.getElementById("aramaSonuclari");
            if (sonuc) sonuc.style.display = "none";
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSite);
    } else {
        initSite();
    }
})();
