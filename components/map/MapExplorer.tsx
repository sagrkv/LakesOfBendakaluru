"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { formatCount } from "@/lib/format";
import type { BBox, LakeSummary, LngLat } from "@/lib/lake";
import { COLLECTION_KEYS, COLLECTIONS, rank, type CollectionKey } from "./collections";
import { boxAround, boxOf, unionBox } from "./geo";
import LakeCanvas, { type Flight, type MapStatus } from "./LakeCanvas";
import LakeCard from "./LakeCard";
import MapNotice from "./MapNotice";
import PhoneBar from "./PhoneBar";
import PhoneDock from "./PhoneDock";
import RankedList from "./RankedList";
import { buildIndex } from "./search";
import SidePanel from "./SidePanel";
import { useLakes } from "./useLakes";
import { useNearMe } from "./useNearMe";
import { useCollectionParam, useHashLake, useWide } from "./useUrlState";

const CARD_WIDTH = 380;
const GAP = 24;
const LAKE_ZOOM = 15;
const COLLECTION_ZOOM = 14;

export default function MapExplorer() {
  const [data, retryData] = useLakes();
  const [collection, setCollection] = useCollectionParam();
  const [selectedId, setSelectedId] = useHashLake();
  const [near, locate] = useNearMe();
  const wide = useWide();
  const [flight, setFlight] = useState<Flight | null>(null);
  const [mapStatus, setMapStatus] = useState<MapStatus>("loading");
  const [reloadKey, setReloadKey] = useState(0);
  const [listCollapsed, setListCollapsed] = useState(false);

  const lakes = data.status === "ready" ? data.lakes : null;
  const here = near.status === "found" ? near.here : null;

  const byId = useMemo(() => new Map((lakes ?? []).map((lake) => [lake.id, lake])), [lakes]);
  const index = useMemo(() => (lakes ? buildIndex(lakes) : null), [lakes]);
  const counts = useMemo(() => {
    if (!lakes) return null;
    const entries = COLLECTION_KEYS.filter((key) => key !== "near").map((key) => [key, rank(key, lakes, null)?.length ?? 0]);
    return Object.fromEntries(entries) as Partial<Record<CollectionKey, number>>;
  }, [lakes]);
  const stats = useMemo(() => {
    if (!lakes) return null;
    const standing = lakes.filter((lake) => lake.status === "exists").length;
    return `${formatCount(standing)} lakes on the map, and ${formatCount(lakes.length - standing)} that disappeared.`;
  }, [lakes]);
  const rows = useMemo(() => (lakes && collection ? rank(collection, lakes, here) : null), [lakes, collection, here]);
  const members = useMemo(() => rows?.map((row) => row.lake.id) ?? null, [rows]);
  const selected = (selectedId && byId.get(selectedId)) || null;

  // A shared link opens on its lake, or on its collection.
  const initialFlight = useMemo<Flight | null>(() => {
    const lake = selectedId ? byId.get(selectedId) : undefined;
    const box = lake ? boxOf(lake) : unionBox((rows ?? []).map((row) => boxOf(row.lake)));
    return box ? { key: 0, box, maxZoom: lake ? LAKE_ZOOM : COLLECTION_ZOOM } : null;
  }, [byId, selectedId, rows]);

  const fly = useCallback((box: BBox, maxZoom: number) => {
    setFlight((prev) => ({ key: (prev?.key ?? 0) + 1, box, maxZoom }));
  }, []);

  const flyNear = (point: LngLat) => {
    if (!lakes) return;
    const nearest = rank("near", lakes, point) ?? [];
    const far = (nearest[0]?.km ?? 0) > 50;
    const box = unionBox([far ? null : boxAround(point), ...nearest.slice(0, 8).map((row) => boxOf(row.lake))]);
    if (box) fly(box, LAKE_ZOOM);
  };

  const findMe = () => locate(flyNear);

  const choose = (key: CollectionKey) => {
    setSelectedId(null);
    setCollection(key);
    setListCollapsed(false);
    if (!lakes) return;
    if (key === "near") {
      if (here) flyNear(here);
      else if (near.status !== "locating") findMe();
      return;
    }
    const box = unionBox((rank(key, lakes, null) ?? []).map((row) => boxOf(row.lake)));
    if (box) fly(box, COLLECTION_ZOOM);
  };

  const pick = (lake: LakeSummary) => {
    setSelectedId(lake.id);
    const box = boxOf(lake);
    if (box) fly(box, LAKE_ZOOM);
  };

  const close = useCallback(() => setSelectedId(null), [setSelectedId]);

  const onStatus = useCallback((status: MapStatus) => {
    // A failed outline load must not be hidden by the map finishing its own load afterwards.
    setMapStatus((prev) => (prev === "error" && status === "ready" ? prev : status));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, close]);

  let notice = null;
  if (mapStatus === "unsupported") {
    notice = (
      <MapNotice>
        This browser cannot draw the map. Turn on hardware acceleration in its settings, or browse the collections {wide ? "on the left" : "below"}.
      </MapNotice>
    );
  } else if (data.status === "error") {
    notice = (
      <MapNotice action={{ label: "Try again", onClick: retryData }}>
        The lake list did not load. Check your connection, then try again.
      </MapNotice>
    );
  } else if (mapStatus === "error") {
    notice = (
      <MapNotice
        action={{
          label: "Try again",
          onClick: () => {
            setMapStatus("ready");
            setReloadKey((n) => n + 1);
          },
        }}
      >
        The lake outlines did not load. Check your connection, then try again.
      </MapNotice>
    );
  } else if (data.status === "loading" || mapStatus === "loading") {
    notice = <MapNotice delayed>Laying out the lakes…</MapNotice>;
  }

  const list = collection ? (
    <RankedList
      collection={collection}
      rows={rows}
      loading={!lakes}
      near={near}
      onLocate={findMe}
      selectedId={selectedId}
      onSelect={pick}
      onBack={() => {
        setSelectedId(null);
        setCollection(null);
      }}
      compact={!wide}
      collapsed={!wide && listCollapsed}
      onToggle={() => setListCollapsed((folded) => !folded)}
    />
  ) : null;

  const announcement = selected
    ? `${selected.name} is open.`
    : collection && rows
      ? `${COLLECTIONS[collection].title}: ${formatCount(rows.length)} lakes.`
      : "";

  return (
    <div className="fixed inset-0 flex flex-col overflow-hidden overscroll-none bg-table lg:flex-row">
      {wide ? (
        <SidePanel
          stats={stats}
          index={index}
          failed={data.status === "error"}
          counts={counts}
          onChoose={choose}
          onPick={pick}
          list={list}
        />
      ) : null}

      <main className="relative min-h-0 min-w-0 flex-1">
        <h1 className="sr-only">Every lake in Bengaluru, on one map</h1>
        <LakeCanvas
          lakes={lakes}
          members={members}
          selectedId={selectedId}
          here={here}
          flight={flight}
          initialFlight={initialFlight}
          padRight={wide && selected ? CARD_WIDTH + GAP : 0}
          reloadKey={reloadKey}
          onSelect={setSelectedId}
          onStatus={onStatus}
        />

        {wide ? (
          (notice || selected) && (
            <div className="pointer-events-none absolute top-6 right-6 z-20 flex flex-col gap-4" style={{ width: CARD_WIDTH }}>
              {notice}
              {selected ? (
                <div className="pointer-events-auto">
                  <LakeCard lake={selected} onClose={close} floating />
                </div>
              ) : null}
            </div>
          )
        ) : (
          <>
            <PhoneBar index={index} failed={data.status === "error"} onPick={pick} />
            {notice ? (
              <div className="pointer-events-none absolute inset-x-4 bottom-16 z-20 flex justify-center">{notice}</div>
            ) : null}
          </>
        )}

        <p className="sr-only" aria-live="polite">
          {announcement}
        </p>
      </main>

      {wide ? null : (
        <PhoneDock
          stats={stats}
          ready={Boolean(lakes)}
          onChoose={choose}
          card={selected ? <LakeCard lake={selected} onClose={close} floating={false} /> : null}
          list={list}
        />
      )}
    </div>
  );
}
