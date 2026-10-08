# Blender Toolkit

Oyun varlığı hazırlarken zaman yiyen tekrarlı işleri ortadan kaldıran on Blender eklentisi: birçok arazi dokusunu
karıştırma, her modele retopoloji, FiveM'e prop ve karakter aktarma ve Unreal Engine 5'e tam bir hat (sert yüzey modelleme,
texel yoğunluğu, dokular, çarpışma, rig ve FBX dışa aktarma) ve çimen, taş, ağaç serpiştiren bir fırça.

**Blender 5.0 – 5.2** (5.0.1 ve 5.2.0 LTS'de test edildi) · GPL-3.0-or-later · Türkçe ve İngilizce arayüz

[English README](README.md)

| Eklenti | Ne yapar | Kılavuz |
|---|---|---|
| **Terrain Blend** | Tek mesh üzerinde istediğin sayıda PBR doku setini vertex group maskeleriyle karıştırır. Eğim, yükseklik veya gürültüden otomatik maske üretir. | [docs/terrain_blend.tr.md](docs/terrain_blend.tr.md) |
| **Retopo Kit** | Prop, araç ve karakter için tek tıkla quad retopoloji; rehber eğriler ve kalite raporu. | [docs/retopo_kit.tr.md](docs/retopo_kit.tr.md) |
| **FiveM Toolkit** | Sollumz üzerine kurulu: prop, MLO iç mekân ve ped kıyafeti için kontrol, düzeltme, derleme ve dışa aktarma. | [docs/fivem_toolkit.tr.md](docs/fivem_toolkit.tr.md) |
| **UE5 Bridge** | Unreal Engine 5 için FBX: statik mesh, modüler iskeletli mesh, animasyon, root motion. | [docs/ue5_bridge.tr.md](docs/ue5_bridge.tr.md) |
| **Texture Kit** | Doku kontrolü, normal map çevirme, ORM paketleme ve Unreal adlı dışa aktarma. | [docs/ue5-pipeline.tr.md](docs/ue5-pipeline.tr.md#texture-kit) |
| **Texel Density** | Her varlığın doku yoğunluğunu ölç, renk olarak göster ve ayarla. | [docs/ue5-pipeline.tr.md](docs/ue5-pipeline.tr.md#texel-density) |
| **Collision Maker** | UBX / USP / UCP / UCX çarpışma şekilleri ve denetleyici, mesh ile birlikte dışa aktarılır. | [docs/ue5-pipeline.tr.md](docs/ue5-pipeline.tr.md#collision-maker) |
| **Hard Surface Kit** | Yıkıcı olmayan bevel, kesici, dizi, olak ve oyuna hazır mesh için Stack'i Uygula. | [docs/ue5-pipeline.tr.md](docs/ue5-pipeline.tr.md#hard-surface-kit) |
| **Game Rig Kit** | UE5 mannequin iskeleti, ağırlıklandırma, IK, yeniden adlandırma ve animasyon retarget. | [docs/ue5-pipeline.tr.md](docs/ue5-pipeline.tr.md#game-rig-kit) |
| **Scatter Brush** | Weight paint ile boyadığın yere ya da tıklama fırçasıyla çimen, taş, ağaç serpiştirir; kategoriler ve kayıtlı rastgelelik. | [docs/scatter_brush.tr.md](docs/scatter_brush.tr.md) |

![Terrain Blend](docs/images/terrain_blend.png)

## Kurulum

1. İstediğin eklentinin `.zip` dosyasını [`dist`](dist/) klasöründen indir (dosyayı aç, indirme düğmesine bas), ya da
   kendin üret: [CONTRIBUTING.md](CONTRIBUTING.md).
2. Blender'da **Edit > Preferences > Get Extensions** aç, sağ üstteki aşağı ok menüsünden **Install from Disk...**
   seç ve zip'i göster. Zip'i açma.
3. Eklentinin kutusunun işaretli olduğundan emin ol. Paneli 3B görünümün yan çubuğunda (`N` tuşu), eklentinin adını
   taşıyan sekmede bulursun.

Eklentiler birbirinden bağımsızdır; yalnızca işine yarayanı kur.

İsteğe bağlı yardımcılar:

- **Retopo Kit** Blender'ın dahili QuadriFlow'u ile çalışır. Rehber eğriler ve daha keskin sonuç için ücretsiz
  [QRemeshify](https://github.com/ksami/QRemeshify) eklentisini de kur.
- **FiveM Toolkit** için [Sollumz](https://docs.sollumz.org) eklentisi gerekir (ücretsiz, GPL). Sollumz'un geliştirme
  sürümleriyle test edildi: 2.8.0 (Blender 5.0) ve 2.8.3 (Blender 5.2).

## Tasarım kuralları

- **Sahnen zarar görmez.** Dışa aktarma geçici kopyalar üzerinde çalışır. Retopoloji orijinali saklar (gizli).
  Verini değiştiren düzeltmeler açık bir düğmedir, sessizce yapılmaz.
- **Gereksiz sınır yok.** Örneğin Terrain Blend istediğin kadar katman alır; yalnızca ekran kartın ya da render motorun
  doku yuvalarını bitirmek üzereyken uyarır.
- **Sorunu anlat, çözümü sun.** FiveM Doktoru ve UE5 iskelet kontrolü neyin yanlış olduğunu düz cümleyle söyler,
  güvenli olanları tek tıkla düzeltir.
- **5.0 ve 5.2'de çalışır.** İki sürüm bazı yerlerde ayrılır (EEVEE doku ve öznitelik sınırları, Vulkan, numpy 1.x/2.x,
  katmanlı action'lar). Her eklentinin iki sürümde de koşan başsız (headless) testi vardır.

## Ne kadar test edildi?

Her eklentinin testi Blender 5.0.1 (OpenGL) ve 5.2.0 LTS (Vulkan) içinde başsız çalışır ve gerçek sahneler kurar:
14 ve 49 doku katmanı, rehber eğrili retopoloji, Sollumz üzerinden prop → MLO → ped dışa aktarma, ve dışa aktarılıp
geri içe aktarılarak denetlenen FBX dosyaları. Neyin test **edilmediği** de açık:

| Alan | Doğrulandı | Doğrulanmadı |
|---|---|---|
| Terrain Blend | İki sürümde 14 ve 49 katmanlı materyal, enhancer, otomatik maske | Çok büyük mesh'ler (milyonlarca vertex) |
| Retopo Kit | Quad sonuç, rehberi izleme, ön ayarlar, rapor | macOS ve Linux'ta QRemeshify |
| FiveM Toolkit | Doktor, LOD'lu ve collision'lı prop, DDS çıktısı, MLO, ped ağırlık aktarma, Sollumz ile dışa aktarma | Sonucun canlı FiveM sunucusunda ya da CodeWalker'da açılması |
| UE5 Bridge | FBX geri okuma: tek kök kemik, leaf kemik yok, boyut, animasyon uzunluğu, root motion çıkarma | Unreal Engine'in kendisinde içe aktarma (elde UE yoktu) |

Bu depodaki ekran görüntüleri, eklentilerin Blender 5.2'de çalışırken bir betikle alınmıştır.

## Diller

Arayüz İngilizce, tam Türkçe çeviri ile gelir (Blender **Preferences > Interface > Language** ayarını izler).

## Lisans

GPL-3.0-or-later, bkz. [LICENSE](LICENSE). `bpy` kullanan Blender eklentileri Blender'ın türev işi sayılır ve ona
uygun lisanslanır.
