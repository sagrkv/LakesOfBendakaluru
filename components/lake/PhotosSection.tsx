import type { CSSProperties } from "react";
import type { LakeRecord } from "@/lib/lake";
import { tiltFor } from "@/components/paper/Slip";
import Section from "./Section";

/** Photos from Wikimedia Commons, pasted like prints, each with the credit its licence asks for. */
export default function PhotosSection({ lake, name }: { lake: LakeRecord; name: string }) {
  const photos = (lake.photos ?? []).slice(0, 9);

  return (
    <Section id="photos" title="Photos" missing="No photos of it on Wikimedia Commons yet." empty={photos.length === 0}>
      {photos.map((photo) => (
        <figure
          key={photo.page}
          className="slip min-w-0 p-2 pb-3"
          style={{ "--tilt": `${tiltFor(photo.title)}deg` } as CSSProperties}
        >
          <a href={photo.page} target="_blank" rel="noreferrer noopener" className="block">
            {/* Commons thumbnails are already sized; next/image would need remote config outside this route. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.thumb}
              width={photo.width}
              height={photo.height}
              alt={`${name}, photographed${photo.date ? ` in ${photo.date.slice(0, 4)}` : ""}`}
              loading="lazy"
              className="aspect-[4/3] h-auto w-full bg-well object-cover"
            />
          </a>
          <figcaption className="label mt-2 px-1 font-normal break-words">
            <a href={photo.page} target="_blank" rel="noreferrer noopener" className="ink-link">
              {photo.credit}
            </a>
            {photo.date ? `, ${photo.date.slice(0, 4)}` : ""}
          </figcaption>
        </figure>
      ))}
    </Section>
  );
}
