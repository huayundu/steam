import git
import argparse
import requests
from tqdm import tqdm


class Pr:
    def __init__(self, repo='.', source_repo=None, token=None):
        self.tqdm = None
        self.repo = git.Repo(repo)
        self.source_repo = source_repo
        self.add_source_repo()
        self.headers = {'Accept': 'application/vnd.github+json',
                        'Authorization': f'Bearer {token}', 'X-GitHub-Api-Version': '2022-11-28'}
        self.owner_name, self.repo_name = self.repo.remote().url.split('/')[-2:]
        self.source_owner_name, self.source_repo_name = self.repo.remote('source').url.split('/')[-2:]
        self.origin_app_list, self.origin_tag_list = self.get_refs_list()
        self.source_app_list, self.source_tag_list = self.get_refs_list(source_repo)
        self.local_app_list = [int(i.name) for i in self.repo.heads if i.name.isdecimal()]
        self.diff_app_set = set()

    def add_source_repo(self):
        if not self.source_repo:
            return
        for i in self.repo.remotes:
            if i.name == 'source':
                return
        self.repo.git.remote('add', 'source', self.source_repo)

    def get_refs_list(self, repo=None):
        app_list = []
        tag_list = []
        if repo:
            result = self.repo.git.ls_remote(repo)
        else:
            result = self.repo.git.ls_remote()
        for i in result.split('\n'):
            if i:
                sha, refs = i.split()
                name = refs.split('/')[-1]
                if refs.startswith('refs/heads/'):
                    if name.isdecimal():
                        app_id = int(name)
                        app_list.append(app_id)
                elif refs.startswith('refs/tags/'):
                    if '_' in name:
                        tag_list.append(name)
        return app_list, tag_list

    def contains(self, tag):
        try:
            return self.repo.git.branch('-r', '--contains', tag).split('/')[-1]
        except git.exc.GitCommandError:
            pass

    def check_diff(self):
        for app_id in self.origin_app_list:
            if app_id not in self.source_app_list:
                self.diff_app_set.add(app_id)
        self.tqdm = tqdm(total=len(self.origin_tag_list))
        for tag in self.origin_tag_list:
            self.tqdm.set_postfix(tag=tag, refresh=False)
            if tag not in self.source_tag_list:
                if name := self.contains(tag):
                    if name.isdecimal():
                        app_id = int(name)
                        if app_id not in self.diff_app_set:
                            self.tqdm.set_postfix(tag=tag, app_id=app_id, refresh=False)
                        self.diff_app_set.add(app_id)
            self.tqdm.update()

    def pr(self):
        self.check_diff()
        for app_id in self.diff_app_set:
            print(app_id)
        for app_id in self.diff_app_set:
            url = f'https://api.github.com/repos/{self.source_owner_name}/{self.source_repo_name}/pulls'
            r = requests.post(url, headers=self.headers,
                              json={'title': str(app_id), 'head': f'{self.owner_name}:{app_id}', 'base': 'main'})
            if r.status_code == 201:
                print(f'pr成功: {app_id}')
            else:
                print(f'pr失败: {app_id}, result: {r.json()}')


parser = argparse.ArgumentParser()
parser.add_argument('-r', '--repo', default='https://github.com/wxy1343/ManifestAutoUpdate')
parser.add_argument('-t', '--token')

if __name__ == '__main__':
    args = parser.parse_args()
    Pr(source_repo=args.repo, token=args.token).pr()
