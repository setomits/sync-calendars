#!/usr/bin/env python

from os.path import exists
from datetime import date, timedelta
from json import dumps

import click
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# カレンダーAPIのスコープ
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    ]


def _authenticate_google_api(target):
    '''
    認証を行う
    '''
    token_file = f'token_{target}.json'
    creds_file = f'credentials_{target}.json'

    creds = None
    if exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return creds


def _get_events(calendar_id, creds, start_time, end_time):
    '''
    予定の取得
    '''

    headers = {
        'Authorization': f'Bearer {creds.token}'
    }

    params = {
        'timeMin': start_time,
        'timeMax': end_time,
        'singleEvents': True,
        'orderBy': 'startTime'
    }

    response = requests.get(
        f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events',
        headers=headers,
        params=params,
    )

    # レスポンスのエラーチェック
    response.raise_for_status()

    # イベントデータを取得
    events = response.json().get('items', [])

    return events


def _delete_events(calendar_id, creds, start_time, end_time):
    '''
    予定の削除
    '''

    headers = {
        'Authorization': f'Bearer {creds.token}'
    }

    events = _get_events(calendar_id, creds, start_time, end_time)
    for event in events:
        requests.delete(
            f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event["id"]}',
            headers=headers,
        )


def _add_event(calendar_id, creds, event):
    '''
    予定の追加
    '''

    headers = {
        'Authorization': f'Bearer {creds.token}'
    }

    body = {
        'summary': event['summary'],
        'start': event['start'],
        'end': event['end']
    }

    requests.post(
        f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events',
        headers=headers,
        data=dumps(body),
    )


def _sync_calendars(calendar_id_src, calendar_id_dst, start_date):
    '''
    予定の同期
    '''

    creds_src = _authenticate_google_api('src')
    creds_dst = _authenticate_google_api('dst')
    start_time = start_date.isoformat() + 'T00:00:00Z'
    end_time = (start_date+timedelta(days=30)).isoformat() + 'T00:00:00Z'

    events = _get_events(calendar_id_src, creds_src, start_time, end_time)
    _delete_events(calendar_id_dst, creds_dst, start_time, end_time)
    for event in events:
        if 'dateTime' not in event['start']:
            continue
        _add_event(calendar_id_dst, creds_dst, event)

@click.group()
def main():
    pass

@main.command()
@click.argument("target", type=click.Choice(["src", "dst"]))
def auth(target):
    _authenticate_google_api(target)

@main.command()
@click.argument("calendar_id_src")
@click.argument("calendar_id_dst")
@click.option("--start-date", type=click.DateTime(formats=["%Y-%m-%d"]), default=date.today, show_default="today")
def sync(calendar_id_src, calendar_id_dst, start_date):
    _sync_calendars(calendar_id_src, calendar_id_dst, start_date)


if __name__ == '__main__':
    main()

