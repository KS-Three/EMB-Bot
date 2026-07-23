(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // ~137 curated Google Fonts, each pointing at a real TTF/OTF served via
  // jsDelivr's mirror of the `google/fonts` GitHub repo (CORS-friendly, and
  // NOT woff2 -- opentype.js cannot inflate woff2). Some entries are
  // variable-font files (bracketed axis tags, e.g. "Roboto[wdth,wght].ttf");
  // opentype.js parses these fine and loads the default instance.
  const FONTS = [
    // --- Sans-serif ---
    { family: "Roboto", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/roboto/Roboto%5Bwdth%2Cwght%5D.ttf" },
    { family: "Open Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf" },
    { family: "Lato", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/lato/Lato-Regular.ttf" },
    { family: "Montserrat", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/montserrat/Montserrat%5Bwght%5D.ttf" },
    { family: "Poppins", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/poppins/Poppins-Regular.ttf" },
    { family: "Inter", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf" },
    { family: "Noto Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf" },
    { family: "Source Sans 3", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/sourcesans3/SourceSans3%5Bwght%5D.ttf" },
    { family: "Nunito", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/nunito/Nunito%5Bwght%5D.ttf" },
    { family: "Nunito Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/nunitosans/NunitoSans%5BYTLC%2Copsz%2Cwdth%2Cwght%5D.ttf" },
    { family: "Raleway", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/raleway/Raleway%5Bwght%5D.ttf" },
    { family: "Ubuntu", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ufl/ubuntu/Ubuntu-Regular.ttf" },
    { family: "Work Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/worksans/WorkSans%5Bwght%5D.ttf" },
    { family: "Rubik", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/rubik/Rubik%5Bwght%5D.ttf" },
    { family: "Karla", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/karla/Karla%5Bwght%5D.ttf" },
    { family: "Mulish", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/mulish/Mulish%5Bwght%5D.ttf" },
    { family: "Barlow", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/barlow/Barlow-Regular.ttf" },
    { family: "DM Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf" },
    { family: "Manrope", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/manrope/Manrope%5Bwght%5D.ttf" },
    { family: "PT Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ptsans/PT_Sans-Web-Regular.ttf" },
    { family: "Fira Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/firasans/FiraSans-Regular.ttf" },
    { family: "Titillium Web", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/titilliumweb/TitilliumWeb-Regular.ttf" },
    { family: "Cabin", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cabin/Cabin%5Bwdth%2Cwght%5D.ttf" },
    { family: "Hind", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/hind/Hind-Regular.ttf" },
    { family: "Quicksand", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/quicksand/Quicksand%5Bwght%5D.ttf" },
    { family: "Heebo", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/heebo/Heebo%5Bwght%5D.ttf" },
    { family: "Oxygen", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/oxygen/Oxygen-Regular.ttf" },
    { family: "Assistant", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/assistant/Assistant%5Bwght%5D.ttf" },
    { family: "Overpass", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/overpass/Overpass%5Bwght%5D.ttf" },
    { family: "Jost", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/jost/Jost%5Bwght%5D.ttf" },
    { family: "Archivo", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/archivo/Archivo%5Bwdth%2Cwght%5D.ttf" },
    { family: "IBM Plex Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ibmplexsans/IBMPlexSans%5Bwdth%2Cwght%5D.ttf" },
    { family: "Red Hat Display", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/redhatdisplay/RedHatDisplay%5Bwght%5D.ttf" },
    { family: "Sora", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/sora/Sora%5Bwght%5D.ttf" },
    { family: "Outfit", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/outfit/Outfit%5Bwght%5D.ttf" },
    { family: "Space Grotesk", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf" },
    { family: "Urbanist", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/urbanist/Urbanist%5Bwght%5D.ttf" },
    { family: "Figtree", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/figtree/Figtree%5Bwght%5D.ttf" },
    { family: "Plus Jakarta Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf" },
    { family: "Lexend", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/lexend/Lexend%5Bwght%5D.ttf" },
    { family: "Public Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/publicsans/PublicSans%5Bwght%5D.ttf" },
    { family: "Epilogue", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/epilogue/Epilogue%5Bwght%5D.ttf" },
    { family: "Comfortaa", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/comfortaa/Comfortaa%5Bwght%5D.ttf" },
    { family: "Varela Round", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/varelaround/VarelaRound-Regular.ttf" },
    { family: "Signika", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/signika/Signika%5BGRAD%2Cwght%5D.ttf" },
    { family: "Exo 2", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/exo2/Exo2%5Bwght%5D.ttf" },
    { family: "Saira", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/saira/Saira%5Bwdth%2Cwght%5D.ttf" },
    { family: "Krub", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/krub/Krub-Regular.ttf" },
    { family: "Prompt", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/prompt/Prompt-Regular.ttf" },
    { family: "Kanit", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/kanit/Kanit-Regular.ttf" },
    { family: "Maven Pro", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/mavenpro/MavenPro%5Bwght%5D.ttf" },
    { family: "Catamaran", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/catamaran/Catamaran%5Bwght%5D.ttf" },
    { family: "Asap", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/asap/Asap%5Bwdth%2Cwght%5D.ttf" },
    { family: "Yanone Kaffeesatz", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/yanonekaffeesatz/YanoneKaffeesatz%5Bwght%5D.ttf" },
    { family: "Dosis", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/dosis/Dosis%5Bwght%5D.ttf" },
    { family: "Josefin Sans", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/josefinsans/JosefinSans%5Bwght%5D.ttf" },
    { family: "Baloo 2", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/baloo2/Baloo2%5Bwght%5D.ttf" },

    // --- Serif ---
    { family: "Playfair Display", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" },
    { family: "Merriweather", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/merriweather/Merriweather%5Bopsz%2Cwdth%2Cwght%5D.ttf" },
    { family: "Lora", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/lora/Lora%5Bwght%5D.ttf" },
    { family: "PT Serif", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ptserif/PT_Serif-Web-Regular.ttf" },
    { family: "Noto Serif", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/notoserif/NotoSerif%5Bwdth%2Cwght%5D.ttf" },
    { family: "Crimson Text", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/crimsontext/CrimsonText-Regular.ttf" },
    { family: "Crimson Pro", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/crimsonpro/CrimsonPro%5Bwght%5D.ttf" },
    { family: "Libre Baskerville", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/librebaskerville/LibreBaskerville%5Bwght%5D.ttf" },
    { family: "EB Garamond", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf" },
    { family: "Cormorant", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cormorant/Cormorant%5Bwght%5D.ttf" },
    { family: "Cormorant Garamond", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf" },
    { family: "Spectral", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/spectral/Spectral-Regular.ttf" },
    { family: "Domine", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/domine/Domine%5Bwght%5D.ttf" },
    { family: "Vollkorn", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/vollkorn/Vollkorn%5Bwght%5D.ttf" },
    { family: "Alegreya", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/alegreya/Alegreya%5Bwght%5D.ttf" },
    { family: "Frank Ruhl Libre", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/frankruhllibre/FrankRuhlLibre%5Bwght%5D.ttf" },
    { family: "Source Serif 4", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/sourceserif4/SourceSerif4%5Bopsz%2Cwght%5D.ttf" },
    { family: "IBM Plex Serif", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ibmplexserif/IBMPlexSerif-Regular.ttf" },
    { family: "Neuton", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/neuton/Neuton-Regular.ttf" },
    { family: "Bree Serif", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/breeserif/BreeSerif-Regular.ttf" },
    { family: "Arvo", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/arvo/Arvo-Regular.ttf" },
    { family: "Rokkitt", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/rokkitt/Rokkitt%5Bwght%5D.ttf" },
    { family: "Old Standard TT", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/oldstandardtt/OldStandard-Regular.ttf" },

    // --- Slab / Display ---
    { family: "Roboto Slab", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/apache/robotoslab/RobotoSlab%5Bwght%5D.ttf" },
    { family: "Zilla Slab", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/zillaslab/ZillaSlab-Regular.ttf" },
    { family: "Bitter", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/bitter/Bitter%5Bwght%5D.ttf" },
    { family: "Aleo", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/aleo/Aleo%5Bwght%5D.ttf" },
    { family: "Abril Fatface", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/abrilfatface/AbrilFatface-Regular.ttf" },
    { family: "Lobster", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/lobster/Lobster-Regular.ttf" },
    { family: "Pacifico", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/pacifico/Pacifico-Regular.ttf" },
    { family: "Bebas Neue", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/bebasneue/BebasNeue-Regular.ttf" },
    { family: "Anton", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anton/Anton-Regular.ttf" },
    { family: "Fjalla One", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/fjallaone/FjallaOne-Regular.ttf" },
    { family: "Passion One", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/passionone/PassionOne-Regular.ttf" },
    { family: "Alfa Slab One", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/alfaslabone/AlfaSlabOne-Regular.ttf" },
    { family: "Righteous", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/righteous/Righteous-Regular.ttf" },
    { family: "Bungee", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/bungee/Bungee-Regular.ttf" },
    { family: "Fredoka", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/fredoka/Fredoka%5Bwdth%2Cwght%5D.ttf" },
    { family: "Luckiest Guy", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/apache/luckiestguy/LuckiestGuy-Regular.ttf" },
    { family: "Staatliches", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/staatliches/Staatliches-Regular.ttf" },
    { family: "Archivo Black", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/archivoblack/ArchivoBlack-Regular.ttf" },
    { family: "Oswald", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/oswald/Oswald%5Bwght%5D.ttf" },
    { family: "Squada One", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/squadaone/SquadaOne-Regular.ttf" },
    { family: "Titan One", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/titanone/TitanOne-Regular.ttf" },

    // --- Script / Handwriting ---
    { family: "Dancing Script", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/dancingscript/DancingScript%5Bwght%5D.ttf" },
    { family: "Great Vibes", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/greatvibes/GreatVibes-Regular.ttf" },
    { family: "Sacramento", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/sacramento/Sacramento-Regular.ttf" },
    { family: "Satisfy", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/apache/satisfy/Satisfy-Regular.ttf" },
    { family: "Kaushan Script", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/kaushanscript/KaushanScript-Regular.ttf" },
    { family: "Caveat", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/caveat/Caveat%5Bwght%5D.ttf" },
    { family: "Shadows Into Light", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/shadowsintolight/ShadowsIntoLight.ttf" },
    { family: "Indie Flower", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/indieflower/IndieFlower-Regular.ttf" },
    { family: "Amatic SC", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amaticsc/AmaticSC-Regular.ttf" },
    { family: "Permanent Marker", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/apache/permanentmarker/PermanentMarker-Regular.ttf" },
    { family: "Homemade Apple", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/apache/homemadeapple/HomemadeApple-Regular.ttf" },
    { family: "Courgette", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/courgette/Courgette-Regular.ttf" },
    { family: "Cookie", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cookie/Cookie-Regular.ttf" },
    { family: "Allura", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/allura/Allura-Regular.ttf" },
    { family: "Parisienne", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/parisienne/Parisienne-Regular.ttf" },
    { family: "Marck Script", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/marckscript/MarckScript-Regular.ttf" },
    { family: "Yellowtail", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/apache/yellowtail/Yellowtail-Regular.ttf" },
    { family: "Handlee", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/handlee/Handlee-Regular.ttf" },
    { family: "Patrick Hand", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/patrickhand/PatrickHand-Regular.ttf" },
    { family: "Kalam", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/kalam/Kalam-Regular.ttf" },

    // --- Monospace ---
    { family: "Roboto Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/robotomono/RobotoMono%5Bwght%5D.ttf" },
    { family: "Source Code Pro", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/sourcecodepro/SourceCodePro%5Bwght%5D.ttf" },
    { family: "JetBrains Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf" },
    { family: "IBM Plex Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ibmplexmono/IBMPlexMono-Regular.ttf" },
    { family: "Space Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/spacemono/SpaceMono-Regular.ttf" },
    { family: "Inconsolata", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/inconsolata/static/Inconsolata-Regular.ttf" },
    { family: "Fira Code", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/firacode/FiraCode%5Bwght%5D.ttf" },
    { family: "Fira Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/firamono/FiraMono-Regular.ttf" },
    { family: "PT Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ptmono/PTM55FT.ttf" },
    { family: "Cousine", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cousine/Cousine-Regular.ttf" },
    { family: "Courier Prime", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/courierprime/CourierPrime-Regular.ttf" },
    { family: "Overpass Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/overpassmono/OverpassMono%5Bwght%5D.ttf" },
    { family: "Ubuntu Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ufl/ubuntumono/UbuntuMono-Regular.ttf" },
    { family: "Anonymous Pro", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anonymouspro/AnonymousPro-Regular.ttf" },
    { family: "DM Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/dmmono/DMMono-Regular.ttf" },
    { family: "Azeret Mono", url: "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/azeretmono/AzeretMono%5Bwght%5D.ttf" },
  ];

  // Load an opentype.Font from a URL. Requires the global `opentype` (loaded
  // via CDN script tag in the browser shell) -- NOT referenced at module load
  // time so this file still requires() cleanly under plain Node.
  function loadFont(url) {
    return new Promise((resolve, reject) => {
      const ot = (typeof globalThis !== "undefined" && globalThis.opentype) ||
        (typeof window !== "undefined" && window.opentype);
      if (!ot) {
        reject(new Error("global `opentype` not found (load opentype.js via CDN first)"));
        return;
      }
      ot.load(url, (err, font) => {
        if (err) reject(err instanceof Error ? err : new Error(String(err)));
        else resolve(font);
      });
    });
  }

  // Flatten a cubic Bezier (p0..p3) into `segments` line points (excludes p0,
  // includes the endpoint p3).
  function flattenCubic(p0, p1, p2, p3, segments, out) {
    for (let i = 1; i <= segments; i++) {
      const t = i / segments;
      const mt = 1 - t;
      const x = mt * mt * mt * p0.x + 3 * mt * mt * t * p1.x + 3 * mt * t * t * p2.x + t * t * t * p3.x;
      const y = mt * mt * mt * p0.y + 3 * mt * mt * t * p1.y + 3 * mt * t * t * p2.y + t * t * t * p3.y;
      out.push({ x, y });
    }
  }

  // Flatten a quadratic Bezier (p0,p1,p2) into `segments` line points
  // (excludes p0, includes the endpoint p2).
  function flattenQuadratic(p0, p1, p2, segments, out) {
    for (let i = 1; i <= segments; i++) {
      const t = i / segments;
      const mt = 1 - t;
      const x = mt * mt * p0.x + 2 * mt * t * p1.x + t * t * p2.x;
      const y = mt * mt * p0.y + 2 * mt * t * p1.y + t * t * p2.y;
      out.push({ x, y });
    }
  }

  // Convert an opentype.js Path into an array of closed polygons (arrays of
  // {x,y} points), flattening cubic/quadratic curve commands into polylines
  // with a fixed number of segments per curve.
  function pathToPolygons(path, curveSegments) {
    const segments = curveSegments || 8;
    const polygons = [];
    let current = [];
    let cur = { x: 0, y: 0 };
    let start = { x: 0, y: 0 };

    const commands = (path && path.commands) || [];
    for (const cmd of commands) {
      switch (cmd.type) {
        case "M":
          if (current.length > 1) polygons.push(current);
          current = [{ x: cmd.x, y: cmd.y }];
          cur = { x: cmd.x, y: cmd.y };
          start = { x: cmd.x, y: cmd.y };
          break;
        case "L":
          current.push({ x: cmd.x, y: cmd.y });
          cur = { x: cmd.x, y: cmd.y };
          break;
        case "C":
          flattenCubic(
            cur,
            { x: cmd.x1, y: cmd.y1 },
            { x: cmd.x2, y: cmd.y2 },
            { x: cmd.x, y: cmd.y },
            segments,
            current
          );
          cur = { x: cmd.x, y: cmd.y };
          break;
        case "Q":
          flattenQuadratic(
            cur,
            { x: cmd.x1, y: cmd.y1 },
            { x: cmd.x, y: cmd.y },
            segments,
            current
          );
          cur = { x: cmd.x, y: cmd.y };
          break;
        case "Z":
        case "z":
          if (current.length > 1) polygons.push(current);
          current = [];
          cur = { x: start.x, y: start.y };
          break;
        default:
          break;
      }
    }
    if (current.length > 1) polygons.push(current);
    return polygons;
  }

  // Build the single-region ColorRegion array for a piece of text, laid out
  // with the given opentype.Font. Returns:
  //   [{ rgb:[0,0,0], polygons: Array<Array<{x,y}>> }]
  // Polygons are in PIXEL coordinates (font units scaled to `sizePx`).
  function textToRegions(font, text, opts) {
    const o = opts || {};
    const sizePx = o.sizePx || 200;
    const letterSpacing = o.letterSpacing || 0;

    const polygons = [];

    if (letterSpacing) {
      // Per-glyph layout so we can insert extra spacing between glyphs.
      let x = 0;
      const y = 0;
      const glyphs = font.stringToGlyphs ? font.stringToGlyphs(text) : null;
      if (glyphs) {
        const scale = (1 / font.unitsPerEm) * sizePx;
        for (const glyph of glyphs) {
          const glyphPath = glyph.getPath(x, y, sizePx);
          const polys = pathToPolygons(glyphPath, 8);
          for (const p of polys) polygons.push(p);
          x += (glyph.advanceWidth || 0) * scale + letterSpacing;
        }
      } else {
        const path = font.getPath(text, 0, 0, sizePx);
        const polys = pathToPolygons(path, 8);
        for (const p of polys) polygons.push(p);
      }
    } else {
      const path = font.getPath(text, 0, 0, sizePx);
      const polys = pathToPolygons(path, 8);
      for (const p of polys) polygons.push(p);
    }

    return [{ rgb: [0, 0, 0], polygons }];
  }

  // Per-LETTER layout: returns one group per rendered glyph so callers can
  // assign a stitch angle/slant per letter. Returns:
  //   [{ char, polygons: Array<Array<{x,y}>> }]   (whitespace glyphs omitted)
  // Polygons are in the same pixel space as textToRegions. Falls back to a
  // single whole-string group if the font can't enumerate glyphs.
  function textToLetters(font, text, opts) {
    const o = opts || {};
    const sizePx = o.sizePx || 200;
    const letterSpacing = o.letterSpacing || 0;
    const glyphs = font.stringToGlyphs ? font.stringToGlyphs(text) : null;
    const chars = Array.from(text);
    const out = [];
    if (glyphs && font.unitsPerEm) {
      const scale = (1 / font.unitsPerEm) * sizePx;
      let x = 0;
      for (let gi = 0; gi < glyphs.length; gi++) {
        const glyph = glyphs[gi];
        const polys = pathToPolygons(glyph.getPath(x, 0, sizePx), 8);
        if (polys.length) out.push({ char: chars[gi] != null ? chars[gi] : "", polygons: polys });
        x += (glyph.advanceWidth || 0) * scale + letterSpacing;
      }
    } else {
      const polys = pathToPolygons(font.getPath(text, 0, 0, sizePx), 8);
      if (polys.length) out.push({ char: text, polygons: polys });
    }
    return out;
  }

  return { FONTS, loadFont, textToRegions, textToLetters, pathToPolygons };
});
