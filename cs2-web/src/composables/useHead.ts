export function useHead(title: string, description: string, image?: string) {
  const fullTitle = `${title} — CS2 Tactics Lab`;
  document.title = fullTitle;

  const setMeta = (attr: string, value: string, isProperty: boolean) => {
    const selector = isProperty
      ? `meta[property="${attr}"]`
      : `meta[name="${attr}"]`;
    let el = document.querySelector(selector) as HTMLMetaElement | null;
    if (!el) {
      el = document.createElement('meta');
      if (isProperty) el.setAttribute('property', attr);
      else el.setAttribute('name', attr);
      document.head.appendChild(el);
    }
    el.setAttribute('content', value);
  };

  setMeta('description', description, false);
  setMeta('og:title', fullTitle, true);
  setMeta('og:description', description, true);
  setMeta('og:type', 'website', true);
  setMeta('og:url', window.location.href, true);
  setMeta('twitter:card', image ? 'summary_large_image' : 'summary', false);
  setMeta('twitter:title', fullTitle, false);
  setMeta('twitter:description', description, false);
  if (image) setMeta('og:image', image, true);
  if (image) setMeta('twitter:image', image, false);

  let canonical = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
  if (!canonical) {
    canonical = document.createElement('link');
    canonical.setAttribute('rel', 'canonical');
    document.head.appendChild(canonical);
  }
  canonical.setAttribute('href', window.location.href);
}
