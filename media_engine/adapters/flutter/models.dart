class PanoramaTile {
  final int level;
  final int x;
  final int y;
  final int width;
  final int height;
  final String url;

  const PanoramaTile({
    required this.level,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.url,
  });

  factory PanoramaTile.fromJson(int level, Map<String, dynamic> json) => PanoramaTile(
        level: level,
        x: json['x'] as int,
        y: json['y'] as int,
        width: json['width'] as int,
        height: json['height'] as int,
        url: json['url'] as String,
      );
}

class PanoramaLevel {
  final int level;
  final int width;
  final int height;
  final int cols;
  final int rows;
  final int tileSize;
  final Map<String, List<PanoramaTile>> formats;

  const PanoramaLevel({
    required this.level,
    required this.width,
    required this.height,
    required this.cols,
    required this.rows,
    required this.tileSize,
    required this.formats,
  });

  factory PanoramaLevel.fromJson(Map<String, dynamic> json) {
    final level = json['level'] as int;
    final rawFormats = Map<String, dynamic>.from(json['formats'] as Map);
    return PanoramaLevel(
      level: level,
      width: json['width'] as int,
      height: json['height'] as int,
      cols: json['cols'] as int,
      rows: json['rows'] as int,
      tileSize: json['tile_size'] as int,
      formats: rawFormats.map((key, value) => MapEntry(
            key,
            (value as List)
                .map((e) => PanoramaTile.fromJson(level, Map<String, dynamic>.from(e as Map)))
                .toList(),
          )),
    );
  }
}

class PanoramaManifest {
  final String assetId;
  final String projection;
  final String preview;
  final List<PanoramaLevel> levels;

  const PanoramaManifest({
    required this.assetId,
    required this.projection,
    required this.preview,
    required this.levels,
  });

  factory PanoramaManifest.fromJson(Map<String, dynamic> json) => PanoramaManifest(
        assetId: json['asset_id'] as String,
        projection: json['projection'] as String? ?? 'equirectangular',
        preview: json['preview'] as String? ?? '',
        levels: (json['levels'] as List? ?? const [])
            .map((e) => PanoramaLevel.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
      );
}
