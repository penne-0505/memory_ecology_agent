---
created:
---
![NVIDIAが2030年まで続くRTX Sparkロードマップを公開——Vera Rubin、Rosa Feynman、DGX Stationまで含む長期戦略の全貌](https://media.xenospectrum.com/large_RTX_Spark_successors_for_laptops_and_desktops_roadmap_07f65700e1.webp)

NVIDIAが2030年まで続くRTX Sparkロードマップを公開——Vera Rubin、Rosa Feynman、DGX Stationまで含む長期戦略の全貌

TL;DR
- 何が起きた: NVIDIAはComputex 2026の基調講演で、RTX SparkおよびDGX Station for Windowsの複数世代にわたるロードマップを公式に確認し、2026年のGrace Blackwell（Blackwell + LPDDR5X）を皮切りに、2027〜2028年のVera Rubin Spark（LPDDR6対応）、2029〜2030年のRosa Feynman Sparkまでを提示した。
- なぜ重要か: ARMベースのWindows PCというエコシステムはこれまで試行錯誤の繰り返しだったが、NVIDIAが時価総額世界首位の企業として複数世代の継続を公約したことで、OEMメーカーやソフトウェアベンダーが本格投資を判断する根拠が生まれた。
- 次に見るべき点: Grace Blackwell RTX Sparkの実市場でのパフォーマンス検証結果、Vera世代でのCPUコア設計の具体的な変更点（MediaTekとの共同開発継続か否か）、LPDDR6の帯域幅向上が実際のAI推論スループットにどう反映されるか。

NVIDIAの RTX Spark は、同社初のARMベースSoC製品として2026年に登場する。 Grace CPU と Blackwell アーキテクチャのGPUを統合したこのチップは、 ユニファイドメモリ によって最大600GB/sの帯域幅を実現し、RTX 5070クラスの統合グラフィックスを搭載する。ラップトップ向けから始まり、コンパクトデスクトップへも展開される予定だ。

しかしComputex 2026でCEOのJensen Huangが発表した内容の核心は、現行世代の仕様詳細ではなかった。2030年まで続く複数世代のロードマップをOEMパートナーと世間の前に明示したことそのものが、最大のメッセージだった。ARMベースWindowsエコシステムにおいては、 Qualcomm のような先行プレイヤーでさえ継続性への懸念を抱えてきた。NVIDIAはその不安を、長期コミットメントという形で正面から払拭しにきた。

AD

## Grace Blackwellから始まる三世代の連鎖

![RTX-Spark-successors-for-laptops-and-desktops-roadmap.jpg](https://media.xenospectrum.com/large_RTX_Spark_successors_for_laptops_and_desktops_roadmap_07f65700e1.webp)

2026年に投入される第一世代のRTX Sparkは、Grace Blackwell Sparkシリコンを中核に持ち、LPDDR5Xメモリを採用する。同時期に発表された DGX Station for Windows は、GB300 Grace Blackwell Ultra Desktopスーパーチップをベースとし、72コアのGrace CPUと、HBM3eを搭載したBlackwell Ultra GPUをNVLink-C2Cで接続する構成だ。

コヒーレントメモリ容量は最大748GB、FP4精度での演算性能は最大20ペタFLOPSに達し、最大1兆パラメータのAIモデルをローカルで稼働させられるとNVIDIAは主張する。DGX Station for Windowsは2026年第4四半期にASUS、Dell Technologies、GIGABYTE、HP、MSI、Supermicroから出荷される予定だ。

2027〜2028年の第二世代となる Vera Rubin Spark は、次世代の Vera CPU と Rubin アーキテクチャのGPUを組み合わせ、LPDDR6メモリを採用する点が技術的に注目される。現行のGrace Blackwellがユニファイドメモリで600GB/sの帯域幅を実現しているのに対し、Vera Rubin世代ではLPDDR6の導入によってさらに高い帯域幅と電力効率の向上が見込まれる。Vera CPUが具体的にどのようなARMコアアーキテクチャを採用するかは現時点では明らかになっていない。現在のGraceが比較的旧世代のARMデザインに基づいているのに対し、Vera世代では新しいコアへの移行が観測者の間で予測されている。なお、NVIDIAが現行RTX Sparkで MediaTek との共同設計を採用していることは知られているが、Vera以降もこの提携が維持されるかどうかはロードマップ上では明示されていない。

DGX Stationの同世代品についても、Rubin架構とHBM4メモリ、Vera CPU、そして ConnectX-9 （CX9）による1600Gbpsネットワーク対応が示されている。この性能密度は、ハイパースケーラーのデータセンターとほぼ同等のハードウェアを「デスクサイド」で稼働させる未来を指し示している。

## Rosa Feynman Sparkの登場と2029〜2030年展望

第三世代の Rosa Feynman Spark は2029〜2030年を対象とする。RosaはVera同様NVIDIA独自のCPUアーキテクチャであり、 Feynman は現在開発が進むGPUアーキテクチャの名称だ。メモリ規格についてロードマップは明言しておらず、LPDDR6が引き続き採用されるか、あるいはさらに後継規格へ移行するかは未確定のままだ。

DGX Station世代の対応製品では、Feynman GPU、 Rosa CPU 、 ConnectX-10 （CX10）ネットワーク、そして「HBM Next」と記載された次世代HBMメモリの搭載が示されている。公式ロードマップ上にRosa Feynman Sparkの名称が初めて明記されたのは今回が初めてであり、NVIDIAが2030年に向けてSparkラインアップを維持し続けることを対外的に宣言した意味は大きい。

AD

## QualcommとApple Silicon——NVIDIAが対峙する構図

ARMベースのWindows PCに本格参入したプレイヤーといえば、まずQualcommのSnapdragon Xシリーズが挙げられる。しかし消費者認知と開発者エコシステムの観点では、AppleがM系チップで確立した地位が圧倒的な比較対象となる。NVIDIAはComputex前日のブリーフィングセッションで「RTX SparkがWindows on ARMで成功できるのは、我々がプラットフォームの実現に全力を投じているからだ」と明言した。

この発言の背景には、NVIDIAがハードウェアメーカーであると同時に、CUDAエコシステムを頂点とするソフトウェアスタックの開発企業でもあるという事実がある。AppleはMetal、CoreML、Neural Engineという垂直統合型のスタックを持ち、QualcommはスナップドラゴンのモバイルDNAを引き継いでいる。それに対してNVIDIAは、データセンターからエッジまでを貫くCUDA、TensorRT、NIMs（NVIDIA Inference Microservices）などのソフトウェア資産をPC向けに展開できる立場にある。

Jensen HuangはComputex基調講演中に、NVIDIAの製品がバッテリー動作中でも007 First LightやForza Horizon 6といったAAA向けタイトルを1440p・100FPSで動作させる映像を実演で披露した。ただしこれはあくまでデモ段階の映像であり、量産モデルでの実測値が公表されるまで、実効性能の最終評価は留保が必要だ。

## OEMとソフトウェアパートナーにとっての意味

技術的な仕様と同じくらい重要なのが、このロードマップが持つビジネス的な含意だ。ハードウェアベンダーが特定のプラットフォームに向けて設計や製造の投資を行う場合、少なくとも2〜3世代分の継続が保証されていなければ採算が合わない。NVIDIAが2026年のGrace Blackwellを「スタート地点」として2030年まで続く道筋を示したことは、ASUS、Dell、HP、Lenovoといったティア1 OEMに対して、このエコシステムに賭ける根拠を与える。

ソフトウェア開発者の観点でも、WindowsアプリケーションのネイティブARM最適化は、これまで「対応しても市場が広がらない」というジレンマに直面してきた。アプリ開発者がARMネイティブ最適化を施せば施すほど、ユーザー体験は向上し、NVIDIAのSoCが選ばれる理由が強化される。このサイクルを起動させるには、NVIDIAのコミットメントが先行する必要があった。

DGX Station for Windowsはこれとやや異なる市場向けだ。企業のAIエンジニア、データサイエンティスト、ローカルエージェント開発者などを対象とし、クラウドの従量課金コストを回避しながら大規模なAI推論をオンプレミスで行いたい需要に応える。最大1兆パラメータのモデルをローカル実行できるという仕様は、エンタープライズのセキュリティポリシーやデータ主権の要件を満たしながらAI活用を進めたい組織に直接訴求する。

AD

## RTX Spark: NVIDIAが「PCの新時代」を宣言するまでの文脈

NVIDIAがPC向けのSoCを独自設計するのは、データセンター向けのGrace Hopperを経て得た経験を土台にしている。データセンター向けではGrace CPUとH100/H200 GPUをNVLink-C2Cで接続するアーキテクチャをすでに実績化しており、そのコンセプトをPC向けの電力・放熱制約の中に押し込む試みがRTX Sparkといえる。

20コアのARMベースGrace CPUを搭載する現行世代は、x86陣営のCore Ultra 200シリーズやRyzen AI 300シリーズとの正面比較を控えながら、AIワークロードにおける優位性をアピールしている。2026年後半（Fall 2026）に量産モデルが流通し始めれば、独立したベンチマークが性能の実像を明らかにするだろう。その結果が、2027年のVera Rubin Sparkへの市場の期待値を規定することになる。

## この記事のキーワード

- [RTX Spark](https://xenospectrum.com/entity/tech-product/rtx-spark/)
- [Grace CPU](https://xenospectrum.com/entity/tech-product/grace-cpu/)
- [Blackwell](https://xenospectrum.com/entity/term/blackwell/)
- [ユニファイドメモリ](https://xenospectrum.com/entity/term/entity-418701c8-54aede/)
- [DGX Station for Windows](https://xenospectrum.com/entity/tech-product/dgx-station-for-windows/)
- [Vera Rubin Spark](https://xenospectrum.com/entity/tech-product/vera-rubin-spark/)
- [Vera CPU](https://xenospectrum.com/entity/tech-product/vera-cpu/)
- [Rubin](https://xenospectrum.com/entity/term/rubin/)
- [Rosa Feynman Spark](https://xenospectrum.com/entity/tech-product/rosa-feynman-spark/)
- [Rosa CPU](https://xenospectrum.com/entity/tech-product/rosa-cpu/)
- [Feynman](https://xenospectrum.com/entity/term/feynman/)
- [ConnectX-9](https://xenospectrum.com/entity/tech-product/connectx-9/)

## この記事はいかがでしたか？

一緒に読みたい・使いたいアイテム

AD