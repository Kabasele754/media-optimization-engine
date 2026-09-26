class MediaVariant {
  final int width;
  final int height;
  final String url;
  final int bytes;
  final int quality;

  const MediaVariant({
    required this.width,
    required this.height,
    required this.url,
    this.bytes = 0,
    this.quality = 0,
  });

  factory MediaVariant.fromJson(Map<String, dynamic> json) => MediaVariant(
        width: (json['width'] as num?)?.toInt() ?? 0,
        height: (json['height'] as num?)?.toInt() ?? 0,
        url: (json['url'] ?? '').toString(),
        bytes: (json['bytes'] as num?)?.toInt() ?? 0,
        quality: (json['quality'] as num?)?.toInt() ?? 0,
      );
}

class MediaManifest {
  final String id;
  final String status;
  final int width;
  final int height;
  final String profile;
  final String dominantColor;
  final String blurhash;
  final String placeholderDataUrl;
  final String originalUrl;
  final MediaVariant? fallback;
  final Map<String, List<MediaVariant>> variants;

  const MediaManifest({
    required this.id,
    required this.status,
    required this.width,
    required this.height,
    required this.profile,
    required this.variants,
    this.dominantColor = '',
    this.blurhash = '',
    this.placeholderDataUrl = '',
    this.originalUrl = '',
    this.fallback,
  });

  factory MediaManifest.fromJson(Map<String, dynamic> json) {
    final rawVariants =
        Map<String, dynamic>.from(json['variants'] as Map? ?? const {});
    final parsed = <String, List<MediaVariant>>{};
    for (final entry in rawVariants.entries) {
      final items = (entry.value as List? ?? const [])
          .whereType<Map>()
          .map((item) => MediaVariant.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList()
        ..sort((a, b) => a.width.compareTo(b.width));
      parsed[entry.key] = items;
    }

    return MediaManifest(
      id: (json['id'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      width: (json['width'] as num?)?.toInt() ?? 0,
      height: (json['height'] as num?)?.toInt() ?? 0,
      profile: (json['profile'] ?? '').toString(),
      dominantColor: (json['dominant_color'] ?? '').toString(),
      blurhash: (json['blurhash'] ?? '').toString(),
      placeholderDataUrl: (json['placeholder_data_url'] ?? '').toString(),
      originalUrl: (json['original_url'] ?? '').toString(),
      fallback: json['fallback'] is Map
          ? MediaVariant.fromJson(
              Map<String, dynamic>.from(json['fallback'] as Map),
            )
          : null,
      variants: parsed,
    );
  }

  MediaVariant? select({
    required double logicalWidth,
    required double devicePixelRatio,
    String preferredFormat = 'webp',
  }) {
    final target = (logicalWidth * devicePixelRatio).ceil().clamp(1, 10000);
    final order = <String>[preferredFormat, 'webp', 'avif'];

    for (final format in order.toSet()) {
      final candidates = variants[format];
      if (candidates == null || candidates.isEmpty) continue;

      for (final candidate in candidates) {
        if (candidate.width >= target) return candidate;
      }
      return candidates.last;
    }

    return fallback;
  }
}
